// Runs the real Outlook add-in script (launchevent.js) against a stand-in Office.js, so its
// behaviour can be tested without Outlook. Input (JSON on stdin):
//   { script, user: {email, name}, outlookDefault: true|false|null,
//     signatures: { "<email>": {status, html, mode} }, composes: ["auto"|"button", ...],
//     mobile: optional { platform: "Android"|"iOS", clientSignatureCheck: "missing"|"throws" } }
//   With `mobile`, the compose window behaves like Outlook on iOS/Android: the phone's own
//   signature is already in the body and isClientSignatureEnabledAsync isn't supported.
// Output (JSON on stdout): one result per compose window.
const vm = require("vm");

let input = "";
process.stdin.on("data", (d) => (input += d));
process.stdin.on("end", async () => {
  const cfg = JSON.parse(input);
  const results = [];
  for (const kind of cfg.composes) results.push(await compose(cfg, kind));
  process.stdout.write(JSON.stringify(results));
});

function compose(cfg, kind) {
  return new Promise((resolve) => {
    // A fresh compose window. If the user's own Outlook signature is enabled, Outlook has
    // already put it in the body - as it does in real Outlook.
    const mobile = cfg.mobile || null;
    const state = {
      signature: mobile ? "<p>PHONE OWN SIGNATURE</p>"
        : cfg.outlookDefault === true ? "<p>OUTLOOK OWN SIGNATURE</p>" : null,
      disabledClientSignature: false,
      notifications: [],
      reports: [],
      fetches: [],
    };
    const handlers = {};
    const item = {
      body: {
        setSignatureAsync(html, opts, cb) {
          state.signature = html; // documented: replaces an existing signature
          cb({ status: "succeeded" });
        },
      },
      isClientSignatureEnabledAsync(cb) {
        cb(cfg.outlookDefault === null ? { status: "failed" } : { status: "succeeded", value: cfg.outlookDefault });
      },
      disableClientSignatureAsync(cb) {
        state.disabledClientSignature = true; // would switch Outlook to "No signature"
        cb && cb({ status: "succeeded" });
      },
      notificationMessages: { replaceAsync: (key, msg) => state.notifications.push(msg.message) },
    };
    if (mobile && mobile.clientSignatureCheck === "missing") delete item.isClientSignatureEnabledAsync;
    if (mobile && mobile.clientSignatureCheck === "throws") {
      item.isClientSignatureEnabledAsync = () => { throw new Error("API not supported"); };
    }
    const Office = {
      context: {
        mailbox: { userProfile: { emailAddress: cfg.user.email, displayName: cfg.user.name }, item },
        diagnostics: { platform: mobile ? mobile.platform : "OfficeOnline", version: "test" },
      },
      CoercionType: { Html: "html" },
      MailboxEnums: { ItemNotificationMessageType: { InformationalMessage: "info" } },
      onReady() {},
      actions: { associate: (name, fn) => (handlers[name] = fn) },
    };
    const fetch = async (url) => {
      state.fetches.push(url);
      if (url.includes("/api/outlook/report")) {
        state.reports.push(Object.fromEntries(new URL(url).searchParams));
        return { ok: true, status: 204, text: async () => "", headers: { get: () => null } };
      }
      const email = new URL(url).searchParams.get("email");
      const sig = cfg.signatures[email] || { status: 404, html: "", mode: null };
      return {
        ok: sig.status === 200,
        status: sig.status,
        text: async () => sig.html,
        headers: { get: (h) => (h.toLowerCase() === "x-casterly-signature-mode" ? sig.mode : null) },
      };
    };
    const context = vm.createContext({ Office, fetch, console: { log() {} }, setTimeout, String, Error, URL });
    vm.runInContext(cfg.script, context);
    const name = kind === "button" ? "insertCasterlySignature" : "onNewMessageComposeHandler";
    handlers[name]({ completed: () => resolve(state) });
  });
}
