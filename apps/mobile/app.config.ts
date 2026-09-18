import { ExpoConfig, ConfigContext } from "expo/config";

function isLoopback(url: string): boolean {
  return /https?:\/\/(localhost|127\.0\.0\.1|10\.0\.2\.2)(:|\/|$)/i.test(url);
}

function resolveApiUrl(): string {
  const fromEnv = process.env.EXPO_PUBLIC_API_URL;
  const profile = process.env.EAS_BUILD_PROFILE;
  if (profile === "production") {
    if (!fromEnv || isLoopback(fromEnv)) {
      throw new Error(
        "EXPO_PUBLIC_API_URL must be a public HTTPS origin for production EAS builds (set an EAS secret).",
      );
    }
    return fromEnv;
  }
  return fromEnv ?? "http://127.0.0.1:8000";
}

function resolveAppKey(): string {
  const fromEnv = process.env.EXPO_PUBLIC_APP_KEY;
  if (process.env.EAS_BUILD_PROFILE === "production") {
    if (!fromEnv) {
      throw new Error("EXPO_PUBLIC_APP_KEY must be set for production EAS builds (set an EAS secret).");
    }
    return fromEnv;
  }
  return fromEnv ?? "dev-app-key";
}

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: "Saha",
  slug: "saha",
  scheme: "saha",
  version: "1.0.0",
  orientation: "portrait",
  icon: "./assets/icon.png",
  userInterfaceStyle: "light",
  ios: {
    supportsTablet: false,
    bundleIdentifier: "com.saha.sloka",
    infoPlist: {
      ITSAppUsesNonExemptEncryption: false,
    },
    privacyManifests: {
      NSPrivacyCollectedDataTypes: [
        {
          NSPrivacyCollectedDataType: "NSPrivacyCollectedDataTypeSearchHistory",
          NSPrivacyCollectedDataTypeLinked: false,
          NSPrivacyCollectedDataTypeTracking: false,
          NSPrivacyCollectedDataTypePurposes: [
            "NSPrivacyCollectedDataTypePurposeAppFunctionality",
          ],
        },
        {
          NSPrivacyCollectedDataType: "NSPrivacyCollectedDataTypeOtherUserContent",
          NSPrivacyCollectedDataTypeLinked: false,
          NSPrivacyCollectedDataTypeTracking: false,
          NSPrivacyCollectedDataTypePurposes: [
            "NSPrivacyCollectedDataTypePurposeAppFunctionality",
          ],
        },
      ],
    },
  },
  android: {
    adaptiveIcon: {
      foregroundImage: "./assets/adaptive-icon.png",
      backgroundColor: "#C45C26",
    },
    package: "com.saha.sloka",
  },
  plugins: [
    "expo-router",
    "expo-font",
    [
      "expo-splash-screen",
      {
        backgroundColor: "#FBF6EE",
        image: "./assets/splash-icon.png",
        resizeMode: "contain",
      },
    ],
  ],
  experiments: {
    typedRoutes: true,
  },
  extra: {
    apiUrl: resolveApiUrl(),
    appKey: resolveAppKey(),
    eas: {
      projectId: process.env.EAS_PROJECT_ID,
    },
  },
  owner: process.env.EXPO_OWNER,
});
