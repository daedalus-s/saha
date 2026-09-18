#!/usr/bin/env python3
"""App Store compliance scan for an Expo/React Native app with a Python backend.

Usage:
    python compliance_scan.py --staged            # files in `git diff --cached`, plus repo-wide config checks
    python compliance_scan.py --all               # entire repository
    python compliance_scan.py <path> [<path>...]  # explicit files/directories
    add --json for machine-readable output, --no-global to skip repo-wide config/docs/dependency checks

Each finding carries a rule id (see rules.md), a severity, a location, and the guideline it maps to:
    BLOCKER   build/submission will fail or the app will certainly be rejected
    REQUIRED  a guideline requirement is not met in code or config
    VERIFY    cannot be decided statically; a human must confirm
    INFO      housekeeping before submission

Standard library only. Heuristic: findings are leads for the reviewer, not verdicts.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__", ".git", "dist", "build", ".expo", ".cache", ".cache-test", "ios", "android"}
SOURCE_EXT = {".ts", ".tsx", ".js", ".jsx", ".py"}
MOBILE_EXT = {".ts", ".tsx", ".js", ".jsx"}

# --------------------------------------------------------------------------- knowledge tables

# package -> (Info.plist purpose strings that must exist, guideline)
PERMISSION_PACKAGES: dict[str, tuple[list[str], str]] = {
    "expo-camera": (["NSCameraUsageDescription", "NSMicrophoneUsageDescription"], "5.1.1(ii)"),
    "react-native-vision-camera": (["NSCameraUsageDescription"], "5.1.1(ii)"),
    "expo-image-picker": (["NSPhotoLibraryUsageDescription", "NSCameraUsageDescription"], "5.1.1(ii)"),
    "expo-media-library": (["NSPhotoLibraryUsageDescription", "NSPhotoLibraryAddUsageDescription"], "5.1.1(ii)"),
    "expo-location": (["NSLocationWhenInUseUsageDescription"], "5.1.5"),
    "@react-native-community/geolocation": (["NSLocationWhenInUseUsageDescription"], "5.1.5"),
    "expo-contacts": (["NSContactsUsageDescription"], "5.1.1(ii)"),
    "expo-calendar": (["NSCalendarsUsageDescription", "NSRemindersUsageDescription"], "5.1.1(ii)"),
    "expo-local-authentication": (["NSFaceIDUsageDescription"], "2.5.13"),
    "expo-tracking-transparency": (["NSUserTrackingUsageDescription"], "5.1.2(i)"),
    "expo-speech-recognition": (["NSSpeechRecognitionUsageDescription", "NSMicrophoneUsageDescription"], "5.1.1(ii)"),
    "expo-av": (["NSMicrophoneUsageDescription"], "2.5.14"),
    "expo-audio": (["NSMicrophoneUsageDescription"], "2.5.14"),
    "expo-sensors": (["NSMotionUsageDescription"], "5.1.1(ii)"),
    "react-native-ble-plx": (["NSBluetoothAlwaysUsageDescription"], "5.1.1(ii)"),
    "expo-brightness": ([], "5.1.1(ii)"),
    "expo-notifications": ([], "4.5.4"),
}

TRACKING_SDKS = {
    "react-native-fbsdk-next", "expo-facebook", "@react-native-firebase/analytics", "react-native-appsflyer",
    "react-native-adjust", "@segment/analytics-react-native", "react-native-branch", "mixpanel-react-native",
    "@amplitude/analytics-react-native", "react-native-google-mobile-ads", "expo-ads-admob", "react-native-fbads",
    "@react-native-firebase/messaging", "posthog-react-native",
}
CRASH_SDKS = {"@sentry/react-native", "@bugsnag/react-native", "@react-native-firebase/crashlytics", "expo-insights"}
THIRD_PARTY_LOGIN_SDKS = {
    "@react-native-google-signin/google-signin", "react-native-fbsdk-next", "expo-facebook",
    "@react-native-firebase/auth", "@supabase/supabase-js", "@clerk/clerk-expo", "@auth0/auth0-react-native",
    "react-native-auth0", "expo-auth-session",
}
APPLE_LOGIN_SDKS = {"expo-apple-authentication", "@invertase/react-native-apple-authentication"}
EXTERNAL_PAYMENT_SDKS = {"@stripe/stripe-react-native", "react-native-paypal", "react-native-razorpay", "@paypal/react-native"}
IAP_SDKS = {"react-native-iap", "expo-in-app-purchases", "react-native-purchases", "expo-iap"}
CRYPTO_LIBS = {"react-native-crypto", "crypto-js", "libsodium-wrappers", "react-native-libsodium", "tweetnacl", "react-native-rsa-native", "node-forge"}
DEV_ONLY_IN_DEPENDENCIES = {"expo-dev-client", "react-native-flipper", "reactotron-react-native", "@storybook/react-native"}

RX_HTTP = re.compile(r"""["'`]http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|\$\{|<)[^"'`\s]+""")
RX_SECRET = re.compile(
    r"""(sk-[A-Za-z0-9]{20,}|sk-ant-[A-Za-z0-9\-_]{20,}|AIza[0-9A-Za-z_\-]{35}|BSA[A-Za-z0-9]{25,}|ghp_[A-Za-z0-9]{36}|"""
    r"""(?i:(api[_-]?key|secret|token|password)\s*[:=]\s*["'][A-Za-z0-9_\-/+=]{20,}["']))"""
)
RX_ENV_REF = re.compile(r"process\.env|os\.environ|getenv|Settings\(|extra\.")
RX_PLACEHOLDER_UI = re.compile(r">[^<{]*(lorem ipsum|TODO|FIXME|placeholder text|coming soon)[^<{]*<", re.I)
RX_OTHER_PLATFORM_UI = re.compile(r">[^<{]*\b(Android|Google Play|Play Store|Windows Phone)\b[^<{]*<")
RX_EXTERNAL_PURCHASE = re.compile(r"openURL\([^)]*(buy|purchase|subscribe|pricing|checkout|donate|paypal|patreon|ko-fi|buymeacoffee|stripe)", re.I)
RX_CONSOLE_PII = re.compile(r"console\.(log|info|debug|warn)\([^)]*\b(query|verses|verse|url|body|email|name|response|data)\b", re.I)
RX_PY_LOG_PII = re.compile(r"(?<![\w.])(?:(?:logging|logger|log)\.(?:info|debug|warning|warn|error|exception)|print)\s*\([^)]*\b(query|verses|body|payload|url|text|html)\b", re.I)
RX_AUTH = re.compile(r"\b(signIn|signUp|logIn|login|register|createUser|createAccount|authenticate)\b")
RX_DELETE_ACCOUNT = re.compile(r"delete\s*Account|deleteUser|removeAccount|delete my account", re.I)
RX_AI_CALL = re.compile(r"\b(translate|extract|search|complete|chat|generate|llm|openai|anthropic|gemini)\s*\(", re.I)
RX_AI_DISCLOSURE = re.compile(r"MeaningDisclaimer|DISCLAIMER|AI-generated|AI generated|generated by (an )?AI", re.I)
RX_CONSENT = re.compile(r"(consent|disclosure|acknowledg|agree|allow(ed)?ThirdParty|AiNotice|DataNotice|onboarding)", re.I)
RX_WEBVIEW = re.compile(r"\bWebView\b")
RX_RATING_PROMPT = re.compile(r"(rate|review)\s*(this|the)?\s*app", re.I)
RX_REQUIRED_REASON_API = re.compile(r"\b(UserDefaults|NSUserDefaults|systemUptime|processInfo|fileModificationDate|creationDate|volumeAvailableCapacity|activeInputModes)\b")


@dataclass
class Finding:
    rule: str
    severity: str
    guideline: str
    location: str
    message: str
    remediation: str


SEVERITY_ORDER = {"BLOCKER": 0, "REQUIRED": 1, "VERIFY": 2, "INFO": 3}


class Scanner:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.findings: list[Finding] = []
        self.mobile_root: Path | None = self._find_mobile_root()
        self.api_root: Path | None = self._find_api_root()
        self.deps: dict[str, str] = self._load_deps()
        self.app_config_text: str = self._read_first(["app.config.ts", "app.config.js", "app.json"], self.mobile_root)
        self.eas_text: str = self._read_first(["eas.json"], self.mobile_root)

    # ------------------------------------------------------------------ helpers
    def add(self, rule: str, severity: str, guideline: str, location: Path | str, message: str, remediation: str) -> None:
        loc = self.rel(location) if isinstance(location, Path) else location
        self.findings.append(Finding(rule, severity, guideline, loc, message, remediation))

    def rel(self, p: Path) -> str:
        try:
            return str(p.resolve().relative_to(self.root.resolve())).replace("\\", "/")
        except ValueError:
            return str(p).replace("\\", "/")

    def _find_mobile_root(self) -> Path | None:
        for cand in self.root.rglob("app.config.*"):
            if not any(s in cand.parts for s in SKIP_DIRS):
                return cand.parent
        for cand in self.root.rglob("app.json"):
            if not any(s in cand.parts for s in SKIP_DIRS) and '"expo"' in cand.read_text(encoding="utf-8", errors="replace"):
                return cand.parent
        return None

    def _find_api_root(self) -> Path | None:
        for cand in self.root.rglob("main.py"):
            if not any(s in cand.parts for s in SKIP_DIRS) and "FastAPI(" in cand.read_text(encoding="utf-8", errors="replace"):
                return cand.parent
        return None

    def _read_first(self, names: list[str], base: Path | None) -> str:
        if not base:
            return ""
        for n in names:
            p = base / n
            if p.is_file():
                return p.read_text(encoding="utf-8", errors="replace")
        return ""

    def _load_deps(self) -> dict[str, str]:
        if not self.mobile_root:
            return {}
        p = self.mobile_root / "package.json"
        if not p.is_file():
            return {}
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        deps = dict(data.get("dependencies", {}))
        deps.update({k: f"dev:{v}" for k, v in data.get("devDependencies", {}).items()})
        return deps

    # ------------------------------------------------------------------ repo-wide checks
    def global_checks(self) -> None:
        self.check_app_config()
        self.check_eas()
        self.check_dependencies()
        self.check_docs()
        self.check_api_serves_legal()
        self.check_ai_consent_flow()
        self.check_accounts()

    def check_app_config(self) -> None:
        if not self.mobile_root:
            self.add("CFG-000", "VERIFY", "2.1", "-", "No Expo app config found; mobile checks skipped.", "Run from the repo that contains app.config.ts / app.json.")
            return
        cfg = self.app_config_text
        loc = self.rel(next(self.mobile_root.glob("app.config.*"), self.mobile_root / "app.json"))
        if "bundleIdentifier" not in cfg:
            self.add("CFG-001", "BLOCKER", "submission", loc, "ios.bundleIdentifier is not set.", "Set ios.bundleIdentifier to the App Store Connect bundle ID.")
        if "ITSAppUsesNonExemptEncryption" not in cfg:
            self.add("CFG-002", "REQUIRED", "export compliance", loc,
                     "ITSAppUsesNonExemptEncryption is not declared; every build will prompt for export compliance.",
                     "Add ios.infoPlist.ITSAppUsesNonExemptEncryption: false if the app only uses HTTPS/OS crypto; otherwise file the export documentation.")
        elif re.search(r"ITSAppUsesNonExemptEncryption\s*:\s*false", cfg) and any(d in self.deps for d in CRYPTO_LIBS):
            self.add("CFG-003", "VERIFY", "export compliance", loc,
                     f"ITSAppUsesNonExemptEncryption is false but custom crypto libs are present: {sorted(d for d in CRYPTO_LIBS if d in self.deps)}.",
                     "Confirm the crypto use is exempt (standard algorithms for authentication/HTTPS) or set the key to true and complete export compliance.")
        if "NSAllowsArbitraryLoads" in cfg and re.search(r"NSAllowsArbitraryLoads\s*:\s*true", cfg):
            self.add("CFG-004", "REQUIRED", "ATS / 1.6", loc, "NSAllowsArbitraryLoads is true (ATS disabled globally).",
                     "Remove it or scope exceptions with NSExceptionDomains and be ready to justify them in review notes.")
        if "privacyManifests" not in cfg:
            self.add("CFG-005", "VERIFY", "privacy manifest", loc,
                     "No ios.privacyManifests block. Expo and RN modules ship their own manifests, but app-level required-reason API use and collected data types must be declared by the app.",
                     "Run `npx expo prebuild -p ios --no-install` in a scratch copy and inspect ios/<App>/PrivacyInfo.xcprivacy; add ios.privacyManifests with NSPrivacyCollectedDataTypes (search queries) and any NSPrivacyAccessedAPITypes the app itself uses.")
        if "supportsTablet" not in cfg:
            self.add("CFG-006", "INFO", "2.4.1", loc, "ios.supportsTablet not set (defaults may require iPad screenshots and iPad layout QA).",
                     "Set supportsTablet explicitly; if true, test iPad layouts and provide 13\" screenshots.")
        if re.search(r"""apiUrl[^\n]*(localhost|127\.0\.0\.1)""", cfg) and not re.search(r"EXPO_PUBLIC_API_URL", self.eas_text):
            self.add("CFG-007", "REQUIRED", "2.1", loc,
                     "API URL falls back to localhost and the EAS production profile does not set EXPO_PUBLIC_API_URL; a review build could point at 127.0.0.1 and appear broken.",
                     "Set env.EXPO_PUBLIC_API_URL (and EXPO_PUBLIC_APP_KEY) on the production profile in eas.json or as EAS secrets, and make the fallback fail loudly in production builds.")
        for m in re.finditer(r"(replace-after-eas-init|<your-[^>]+>|CHANGEME|TODO)", cfg):
            self.add("CFG-008", "INFO", "2.1", f"{loc}", f"Placeholder value `{m.group(1)}` in app config.", "Replace before the production build.")
        if re.search(r"""NS\w+UsageDescription\s*:\s*["'][^"']{0,25}["']""", cfg):
            self.add("CFG-009", "REQUIRED", "5.1.1(ii)", loc, "A purpose string is very short/generic.", "Purpose strings must explain the specific in-app use, e.g. 'Saha uses the photo library to save the PDF you export.'")

    def check_eas(self) -> None:
        if not self.eas_text or not self.mobile_root:
            return
        loc = self.rel(self.mobile_root / "eas.json")
        try:
            eas = json.loads(self.eas_text)
        except json.JSONDecodeError:
            self.add("EAS-000", "BLOCKER", "submission", loc, "eas.json is not valid JSON.", "Fix the JSON.")
            return
        prod = eas.get("build", {}).get("production", {})
        if prod.get("developmentClient"):
            self.add("EAS-001", "BLOCKER", "2.1 / 2.5.1", loc, "production profile has developmentClient: true.", "Remove developmentClient from the production profile.")
        if prod.get("distribution") == "internal":
            self.add("EAS-002", "BLOCKER", "submission", loc, "production profile distribution is internal (ad hoc), not store.", "Remove distribution or set it to 'store'.")
        submit = eas.get("submit", {}).get("production", {}).get("ios", {})
        if submit and not submit.get("ascAppId"):
            self.add("EAS-003", "INFO", "submission", loc, "submit.production.ios.ascAppId is empty.", "Fill in after the App Store Connect record exists, or let `eas submit` create it.")
        if "expo-updates" in self.deps and not prod.get("channel"):
            self.add("EAS-004", "VERIFY", "2.5.2", loc, "expo-updates is installed but the production profile has no channel.", "Set a production channel and ensure OTA updates never change the app's primary purpose (2.5.2).")

    def check_dependencies(self) -> None:
        if not self.mobile_root or not self.deps:
            return
        loc = self.rel(self.mobile_root / "package.json")
        cfg = self.app_config_text
        for pkg, (keys, guideline) in PERMISSION_PACKAGES.items():
            if pkg in self.deps:
                missing = [k for k in keys if k not in cfg]
                if missing:
                    self.add("DEP-001", "REQUIRED", guideline, loc,
                             f"`{pkg}` implies protected-resource access but purpose strings are missing from app config: {missing}.",
                             "Add the keys under ios.infoPlist (or the package's config plugin options) with a specific, user-facing purpose. Also declare the data type in App Privacy.")
                elif not keys:
                    self.add("DEP-002", "VERIFY", guideline, loc, f"`{pkg}` is present; confirm its permission prompt appears only in context and the feature degrades gracefully when denied.",
                             "Request permission at the moment of use with a preceding in-app explanation.")
        trackers = sorted(d for d in TRACKING_SDKS if d in self.deps)
        if trackers:
            sev = "REQUIRED" if "NSUserTrackingUsageDescription" not in cfg else "VERIFY"
            self.add("DEP-003", sev, "5.1.2(i) / ATT", loc,
                     f"Analytics/advertising SDKs present: {trackers}. Tracking requires App Tracking Transparency and matching App Privacy labels.",
                     "Add expo-tracking-transparency + NSUserTrackingUsageDescription, gate the SDK until consent, declare 'Used to track you' data types, and confirm each SDK ships a signed privacy manifest.")
        crashers = sorted(d for d in CRASH_SDKS if d in self.deps)
        if crashers:
            self.add("DEP-004", "VERIFY", "App Privacy labels", loc, f"Crash/diagnostics SDKs present: {crashers}.",
                     "Declare Diagnostics (Crash Data, Performance Data) in App Privacy and confirm the SDK's privacy manifest is included.")
        logins = sorted(d for d in THIRD_PARTY_LOGIN_SDKS if d in self.deps)
        if logins and not any(d in self.deps for d in APPLE_LOGIN_SDKS):
            self.add("DEP-005", "REQUIRED", "4.8", loc, f"Third-party login present ({logins}) without Sign in with Apple.",
                     "Add expo-apple-authentication and offer Sign in with Apple as an equivalent option (or another privacy-equivalent login per 4.8).")
        pay = sorted(d for d in EXTERNAL_PAYMENT_SDKS if d in self.deps)
        if pay:
            self.add("DEP-006", "REQUIRED", "3.1.1 / 3.1.5", loc, f"External payment SDKs present: {pay}.",
                     "Digital content/features must use In-App Purchase; external processors are only for physical goods/services consumed outside the app (3.1.5) or approved exceptions. Document which applies.")
        if any(d in self.deps for d in IAP_SDKS):
            self.add("DEP-007", "VERIFY", "3.1.1 / 3.1.2", loc, "In-app purchase SDK present.",
                     "Confirm restore purchases, clear pricing, subscription terms, and that no purchase path bypasses IAP.")
        devs = sorted(d for d in DEV_ONLY_IN_DEPENDENCIES if d in self.deps and not str(self.deps[d]).startswith("dev:"))
        if devs:
            self.add("DEP-008", "INFO", "2.1", loc, f"Development-only packages in production dependencies: {devs}.", "Move to devDependencies or exclude from production builds.")
        if "react-native-webview" in self.deps:
            self.add("DEP-009", "VERIFY", "4.2 / 2.5.6", loc, "react-native-webview present.",
                     "The app must be more than a repackaged website; confirm WebView is used for specific content, not the primary experience.")

    def check_docs(self) -> None:
        docs = self.root / "docs"
        privacy = next((p for p in [docs / "privacy.md", self.root / "PRIVACY.md", self.root / "privacy.md"] if p.is_file()), None)
        terms = next((p for p in [docs / "terms.md", self.root / "TERMS.md"] if p.is_file()), None)
        if not privacy:
            self.add("DOC-001", "REQUIRED", "5.1.1(i)", "docs/privacy.md", "No privacy policy document found in the repo.",
                     "Add a privacy policy covering data collected, purpose, retention, third-party processors (including AI/LLM providers), children, and contact; host it at a public URL for App Store Connect.")
        else:
            text = privacy.read_text(encoding="utf-8", errors="replace").lower()
            required = {
                "third-party processors (search / AI providers)": ("third", "provider"),
                "retention": ("retention", "retain", "kept"),
                "contact": ("contact",),
                "children": ("children", "child"),
                "what is collected": ("collect", "process"),
            }
            for label, keys in required.items():
                if not any(k in text for k in keys):
                    self.add("DOC-002", "REQUIRED", "5.1.1(i)", self.rel(privacy), f"Privacy policy does not appear to cover: {label}.", "Add the section.")
            if re.search(r"(openai|anthropic|google|llm|ai provider|language model)", text) is None and self.api_root and "litellm" in self._read_first(["pyproject.toml"], self.api_root).lower():
                self.add("DOC-003", "REQUIRED", "5.1.2(i)", self.rel(privacy), "Backend uses an LLM but the privacy policy does not name AI/LLM providers as third-party recipients.", "Name the provider category and what is sent to them.")
        if not terms:
            self.add("DOC-004", "INFO", "5.1.1(i) / EULA", "docs/terms.md", "No terms of use found.", "Add terms (Apple's standard EULA applies if none is supplied, but AI-content and third-party-content disclaimers are worth stating).")
        store_doc = docs / "app-store.md"
        if store_doc.is_file():
            t = store_doc.read_text(encoding="utf-8", errors="replace")
            if re.search(r"<your-[^>]+>", t):
                self.add("DOC-005", "INFO", "5.1.1(i)", self.rel(store_doc), "Privacy policy / support URL still contains a placeholder host.", "Replace with the deployed HTTPS URL before filling App Store Connect.")
            if re.search(r"Age rating\s*\|\s*(12\+|17\+)", t):
                self.add("DOC-006", "INFO", "age rating", self.rel(store_doc), "Age rating uses a retired tier (12+/17+).", "Re-answer the updated age-rating questionnaire (4+, 9+, 13+, 16+, 18+).")
            if "Android" in t.split("## Android")[0] and "iPhone only" not in t:
                self.add("DOC-007", "INFO", "2.3.10", self.rel(store_doc), "Listing copy mentions another platform.", "Keep App Store metadata free of references to other mobile platforms.")

    def check_api_serves_legal(self) -> None:
        if not self.api_root:
            return
        main = self.api_root / "main.py"
        text = main.read_text(encoding="utf-8", errors="replace") if main.is_file() else ""
        for route in ("/privacy", "/terms"):
            if f'"{route}"' not in text and f"'{route}'" not in text:
                self.add("API-001", "REQUIRED" if route == "/privacy" else "INFO", "5.1.1(i)", self.rel(main),
                         f"API does not serve {route}; App Store Connect needs a public privacy policy URL.", f"Add a GET {route} route or host the document elsewhere over HTTPS.")
        if "OPEN_PATHS" in text and "/privacy" in text and "/privacy" not in text.split("OPEN_PATHS", 1)[1].split("}", 1)[0]:
            self.add("API-002", "REQUIRED", "5.1.1(i)", self.rel(main), "/privacy is behind the app-key middleware; Apple's reviewer cannot open it.", "Add /privacy and /terms to OPEN_PATHS.")

    def check_ai_consent_flow(self) -> None:
        """Guideline 5.1.2(i): personal data shared with third parties incl. third-party AI needs disclosure + explicit permission."""
        if not self.mobile_root:
            return
        src_files = [p for p in self._iter(self.mobile_root) if p.suffix in MOBILE_EXT]
        sends_to_backend = [p for p in src_files if re.search(r"api\.(search|translate|extract)\(", p.read_text(encoding="utf-8", errors="replace"))]
        if not sends_to_backend:
            return
        has_consent = any(RX_CONSENT.search(p.read_text(encoding="utf-8", errors="replace")) for p in src_files if "test" not in p.name)
        if not has_consent:
            self.add("AI-001", "REQUIRED", "5.1.2(i)", ", ".join(self.rel(p) for p in sends_to_backend[:3]),
                     "User-typed queries and verse text are forwarded to third-party search and AI providers, but no in-app disclosure/consent step was found before the first send.",
                     "Add a one-time disclosure (first search or first 'Show meaning') naming the categories of third parties (web search provider, AI/LLM provider), what is sent, and a link to the privacy policy; store acceptance locally and gate the calls on it.")
        else:
            self.add("AI-002", "VERIFY", "5.1.2(i)", "apps/mobile", "A consent/disclosure component exists.", "Confirm it appears before the first third-party send, names the third-party category, and that declining prevents the send.")

    def check_accounts(self) -> None:
        if not self.mobile_root:
            return
        texts = {p: p.read_text(encoding="utf-8", errors="replace") for p in self._iter(self.mobile_root) if p.suffix in MOBILE_EXT and "test" not in p.name}
        auth_files = [p for p, t in texts.items() if RX_AUTH.search(t) and re.search(r"(signIn|signUp|createUser|createAccount)\s*\(", t)]
        if auth_files and not any(RX_DELETE_ACCOUNT.search(t) for t in texts.values()):
            self.add("ACC-001", "REQUIRED", "5.1.1(v)", ", ".join(self.rel(p) for p in auth_files[:3]),
                     "Account creation/sign-in exists but no in-app account deletion was found.",
                     "Add an in-app 'Delete account' flow that removes the account and associated data (not just deactivation) and is easy to find.")

    # ------------------------------------------------------------------ per-file checks
    def _iter(self, base: Path):
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                yield Path(dirpath) / fn

    def scan_file(self, path: Path) -> None:
        if path.suffix not in SOURCE_EXT | {".json", ".md", ".toml", ".plist", ".xcprivacy"}:
            return
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        lines = text.splitlines()
        is_mobile = self.mobile_root is not None and self.mobile_root in path.parents
        is_api = self.api_root is not None and self.api_root in path.parents
        is_test = "test" in path.name or "tests" in path.parts

        for i, line in enumerate(lines, 1):
            if RX_SECRET.search(line) and not RX_ENV_REF.search(line) and ".example" not in path.name:
                self.add("SRC-001", "BLOCKER", "1.6 / 5.1.1", f"{self.rel(path)}:{i}", "Possible hard-coded credential or provider key.",
                         "Move to server-side settings / EAS secrets; rotate the key if it was ever committed.")
            if is_mobile and RX_HTTP.search(line) and ".example" not in path.name:
                self.add("SRC-002", "REQUIRED", "ATS / 1.6", f"{self.rel(path)}:{i}", "Plain http:// URL in mobile code (blocked by App Transport Security in production).",
                         "Use https://; if unavoidable, add a scoped NSExceptionDomains entry with justification.")
            if is_mobile and path.suffix == ".tsx" and RX_PLACEHOLDER_UI.search(line):
                self.add("SRC-003", "REQUIRED", "2.1", f"{self.rel(path)}:{i}", "Placeholder text in UI.", "Replace with final copy before submission.")
            if is_mobile and path.suffix == ".tsx" and RX_OTHER_PLATFORM_UI.search(line):
                self.add("SRC-004", "INFO", "2.3.10", f"{self.rel(path)}:{i}", "UI text mentions another mobile platform.", "Remove or make platform-conditional.")
            if is_mobile and RX_EXTERNAL_PURCHASE.search(line):
                self.add("SRC-005", "REQUIRED", "3.1.1 / 3.1.3", f"{self.rel(path)}:{i}", "Link that appears to lead to an external purchase/donation page.",
                         "Digital goods must use IAP; donations must go to approved nonprofits via Apple Pay/IAP rules (3.2.1(vi)). Remove or justify under an entitlement.")
            if is_mobile and not is_test and RX_CONSOLE_PII.search(line):
                self.add("SRC-006", "VERIFY", "5.1.1(iii)", f"{self.rel(path)}:{i}", "console output may include user content (query/verses/response).", "Strip logs from production builds or log only status codes.")
            if is_api and not is_test and RX_PY_LOG_PII.search(line):
                self.add("SRC-007", "VERIFY", "5.1.1(iii) / privacy policy", f"{self.rel(path)}:{i}", "Server log line may include user query, page text, or payload.",
                         "Log identifiers and statuses only, or document the retention in the privacy policy.")
            if is_mobile and RX_RATING_PROMPT.search(line) and "StoreReview" not in text:
                self.add("SRC-008", "REQUIRED", "1.1.7 / 5.6.1", f"{self.rel(path)}:{i}", "Custom rating prompt found.", "Use expo-store-review (SKStoreReviewController) only; custom prompts and incentivised reviews are prohibited.")
            if is_mobile and RX_REQUIRED_REASON_API.search(line):
                self.add("SRC-009", "VERIFY", "privacy manifest", f"{self.rel(path)}:{i}", "Possible required-reason API usage in app code.", "Declare the category and reason code in ios.privacyManifests.NSPrivacyAccessedAPITypes.")

        if is_mobile and path.suffix == ".tsx" and not is_test:
            if re.search(r"api\.translate\(", text) and not RX_AI_DISCLOSURE.search(text):
                self.add("SRC-010", "REQUIRED", "1.1 / 2.3.1 / 5.1.2(i)", self.rel(path), "Screen requests AI-generated meaning but does not render the AI disclaimer.",
                         "Render MeaningDisclaimer wherever meanings are shown (and in exported PDFs).")
            if RX_WEBVIEW.search(text):
                self.add("SRC-011", "VERIFY", "4.2 / 2.5.6", self.rel(path), "Screen renders a WebView.", "Confirm the screen is not a generic browser and that the core experience is native.")
        if is_mobile and path.name in ("pdf.ts", "pdf.tsx") or (is_mobile and "buildPdfHtml" in text and "meanings" in text):
            if not RX_AI_DISCLOSURE.search(text):
                self.add("SRC-012", "REQUIRED", "5.2.2 / 1.1", self.rel(path), "PDF export includes AI meanings but does not appear to embed the AI disclaimer or source attribution.",
                         "Include source URL attribution and the AI-generated meaning disclaimer in the PDF HTML.")
        if is_api and "fetch" in path.name and "robots" not in text.lower():
            self.add("SRC-013", "VERIFY", "5.2.2", self.rel(path), "Outbound page fetcher does not reference robots rules.", "Respect robots.txt and rate limits when fetching third-party pages; document it in review notes.")
        if path.suffix == ".xcprivacy" or path.name == "PrivacyInfo.xcprivacy":
            if "NSPrivacyAccessedAPITypes" not in text:
                self.add("SRC-014", "REQUIRED", "privacy manifest", self.rel(path), "Privacy manifest lacks NSPrivacyAccessedAPITypes.", "Declare required-reason API categories with approved reason codes.")

    # ------------------------------------------------------------------ driver
    def run(self, targets: list[Path], do_global: bool) -> None:
        if do_global:
            self.global_checks()
        seen: set[Path] = set()
        for t in targets:
            if t.is_dir():
                for p in self._iter(t):
                    if p not in seen:
                        seen.add(p)
                        self.scan_file(p)
            elif t.is_file() and t not in seen:
                seen.add(t)
                self.scan_file(t)
        # de-duplicate identical findings
        uniq: dict[tuple, Finding] = {}
        for f in self.findings:
            uniq.setdefault((f.rule, f.location, f.message), f)
        self.findings = sorted(uniq.values(), key=lambda f: (SEVERITY_ORDER[f.severity], f.rule, f.location))


def staged_files(root: Path) -> list[Path]:
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"], cwd=root, capture_output=True, text=True)
    if out.returncode != 0:
        print("git diff --cached failed: " + out.stderr.strip(), file=sys.stderr)
        return []
    return [root / line.strip() for line in out.stdout.splitlines() if line.strip()]


def detect_root() -> Path:
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if out.returncode == 0 and out.stdout.strip():
        return Path(out.stdout.strip())
    return Path.cwd()


def render(findings: list[Finding], scope: str) -> str:
    counts = {k: 0 for k in SEVERITY_ORDER}
    for f in findings:
        counts[f.severity] += 1
    lines = [f"App Store compliance scan ({scope})",
             "  " + "  ".join(f"{k}: {v}" for k, v in counts.items()), ""]
    if not findings:
        lines.append("No findings. Manual checks in rules.md still apply.")
    current = None
    for f in findings:
        if f.severity != current:
            current = f.severity
            lines.append(f"== {current} ==")
        lines.append(f"  [{f.rule}] ({f.guideline}) {f.location}")
        lines.append(f"      {f.message}")
        lines.append(f"      -> {f.remediation}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", help="files or directories to scan")
    ap.add_argument("--staged", action="store_true", help="scan files staged in git")
    ap.add_argument("--all", action="store_true", help="scan the whole repository")
    ap.add_argument("--no-global", action="store_true", help="skip repo-wide config/docs/dependency checks")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", default=None)
    args = ap.parse_args(argv)

    root = Path(args.root) if args.root else detect_root()
    if args.staged:
        targets = staged_files(root)
        scope = f"staged: {len(targets)} files"
        if not targets:
            print("Nothing is staged.", file=sys.stderr)
    elif args.all or not args.paths:
        targets = [root]
        scope = "entire repository"
    else:
        targets = [Path(p) if Path(p).is_absolute() else root / p for p in args.paths]
        scope = f"paths: {', '.join(args.paths)}"

    scanner = Scanner(root)
    scanner.run(targets, do_global=not args.no_global)

    if args.json:
        print(json.dumps({"scope": scope, "root": str(root), "findings": [asdict(f) for f in scanner.findings]}, indent=2))
    else:
        print(render(scanner.findings, scope))
    return 2 if any(f.severity == "BLOCKER" for f in scanner.findings) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
