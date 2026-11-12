# 🙋‍♂️ FREQUENTLY ASKED QUESTIONS (FAQ)

🌐 [Chuyển sang bản tiếng Việt (Vietnamese)](./FAQ.md)

—

Welcome to Duc Nguyen’s (1993) Tweak & App Build Repository. Here is a compilation of frequently asked questions and quick fixes.

### 📌 1. How do I add this repository to Sileo / Feather?
* **For Sileo (Tweaks):** Open Sileo ➡️ Go to *Sources* ➡️ Tap *Add* ➡️ Paste URL: `https://username.github.io/ten-repo/`
* **For Feather (Apps):** Open Feather ➡️ Choose *Add Repository* ➡️ Paste JSON URL: `https://username.github.io/ten-repo/apps.json`

### ❌ 2. Why does the App installed via Feather show “Unable to Verify”?
* **Reason:** The free or shared Certificate you are using has been revoked by Apple.
* **Solution:** Delete the crashed app, import a new valid certificate (clean P12 or DNS) into Feather, and reinstall the app.

### 🛠️ 3. Tweaks installed from Sileo do not appear in Settings or Home Screen?
* Make sure your device has installed necessary dependencies like `PreferenceLoader`, `AltList`, or `RocketBootstrap`.
* Try to **Respring** your device or run the `uicache` command in Terminal to refresh the icon cache.

### 📨 4. How can I request a new App/Tweak or report a bug?
Please navigate to the **Issues** tab of this GitHub repository, create a **New Issue**, and provide the tweak/app name, your iOS version, and screenshots of the bug if possible.

—
*Wish you have a great time tweaking your devices!*