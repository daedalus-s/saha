# Enroll in the Apple Developer Program and link EAS

These steps require *your* Apple ID and payment. They cannot be finished from this repository alone. Work through them in order; the EAS project in `apps/mobile` is already configured to consume the account.

## 1. Apple ID

Use a personal Apple ID with two-factor authentication turned on. This will be the Account Holder.

## 2. Enroll

1. Open [https://developer.apple.com/programs/enroll/](https://developer.apple.com/programs/enroll/)
2. Choose **Individual** unless you have a company D-U-N-S number.
3. Pay the annual fee (USD 99). Approval is typically 24–48 hours; Apple may ask for ID.

You will know it worked when [App Store Connect](https://appstoreconnect.apple.com/) shows Agreements, Tax, and Banking, and **Users and Access** lists you as Account Holder.

## 3. Agreements, tax, banking

In App Store Connect complete the paid-apps agreement (even if the app is free), tax forms, and a bank account. Submission is blocked until these are Active.

## 4. Link the account to EAS

```bash
npm install -g eas-cli
cd apps/mobile
eas login
eas credentials -p ios
```

When EAS asks:

- Bundle identifier: `com.saha.sloka` (must match `app.config.ts`)
- Let EAS **manage credentials** (recommended). It will create a distribution certificate and provisioning profile in your team.

Alternatively, in [expo.dev](https://expo.dev) → Project → Credentials → iOS → set the Apple team.

## 5. Devices for internal testing

Add at least one iPhone UDID in Apple Developer → Devices, or let EAS register it when you run a `preview` / `development` build. TestFlight (production profile) does not need UDIDs.

## Done when

- Apple Developer Program status is **Active**
- `eas credentials -p ios` shows a Distribution Certificate and App Store provisioning profile for `com.saha.sloka`
- You can open App Store Connect and would be able to create an app record (EAS submit can create it for you)
