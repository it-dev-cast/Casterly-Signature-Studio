// Casterly Outlook signature installer.
//
// Every employee downloads this same program from Signature Studio; only the FILE NAME
// differs. It carries the installation key:
//     Casterly-Signature-Setup_<server-url-base64url>.<employee-id>.<key>.exe
// The program reads its own name, fetches that employee's signature from Signature Studio
// and installs it into classic Outlook for Windows as the default signature.
//
// Build with installer\build.ps1 (uses the C# compiler that ships with Windows).
//
// Test options (no Outlook changes):
//     --dry-run <folder>   write the signature files to <folder>, skip the registry, no dialogs
//     --key <key>          use this key instead of reading it from the file name

using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Microsoft.Win32;

[assembly: AssemblyTitle("Casterly Signature Setup")]
[assembly: AssemblyProduct("Signature Studio")]
[assembly: AssemblyCompany("Casterly Private Limited")]
[assembly: AssemblyVersion("1.0.0.0")]

namespace SignatureStudio
{
    class InstallerException : Exception
    {
        public InstallerException(string message) : base(message) { }
    }

    static class Program
    {
        const string Title = "Casterly Signature Setup";
        static readonly string[] OfficeVersions = { "16.0", "15.0" };  // Office 2013 - Microsoft 365

        [STAThread]
        static int Main(string[] args)
        {
            string dryRunFolder = null;
            string key = null;
            for (int i = 0; i < args.Length - 1; i++)
            {
                if (args[i] == "--dry-run") dryRunFolder = args[i + 1];
                if (args[i] == "--key") key = args[i + 1];
            }
            bool dryRun = dryRunFolder != null;

            try
            {
                // New Outlook and Outlook on the web never read signature files, so installing
                // would "succeed" without any visible effect. Say so instead.
                if (!dryRun && !ClassicOutlookIsSetUp())
                    throw new InstallerException(
                        "Classic Outlook isn't set up on this computer, so there is nothing to install into.\n\n" +
                        "If you use the new Outlook or Outlook on the web:\n" +
                        "  1. Open Signature Studio > My Signature and click \"Copy Signature\".\n" +
                        "  2. In Outlook go to Settings > Accounts > Signatures > New signature and paste it.\n" +
                        "  3. Choose it as the default and click Save.\n\n" +
                        "You only need to do this once - new company banners appear automatically.\n\n" +
                        "Nothing was changed on your computer.");

                if (key == null) key = KeyFromFileName();
                string[] parts = key.Split('.');
                if (parts.Length != 3) throw new InstallerException(BadKeyMessage);
                string server = FromBase64Url(parts[0]).TrimEnd('/');
                string employeeId = parts[1];
                string signature = parts[2];

                Dictionary<string, object> data = FetchSignature(server, employeeId, signature);
                string name = (string)data["signature_name"];
                string html = (string)data["html"];
                string text = (string)data["text"];
                string employeeName = (string)data["employee_name"];

                string folder = dryRun ? dryRunFolder : Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), @"Microsoft\Signatures");
                // Only the Signature Studio signature (this one file name) is ever written; other
                // signatures in the folder are never touched. Re-running updates it in place.
                // An older install used the name "Casterly"; it is renamed, not duplicated.
                bool renamedLegacy = RemoveLegacySignature(folder, name);
                bool firstInstall = !renamedLegacy && !File.Exists(Path.Combine(folder, name + ".htm"));
                string backup = WriteSignatureFiles(folder, name, html, text);

                // Make it the default only on first install. On later runs the user's own choice
                // (which may be another signature) is preserved. Never set to "(none)".
                string defaults;
                if (firstInstall)
                {
                    if (!dryRun) SetOutlookDefaults(name);
                    defaults = "set";
                }
                else
                {
                    // If the default pointed at the old name, point it at the new one.
                    if (renamedLegacy && !dryRun) RepointDefaults(LegacyName, name);
                    defaults = renamedLegacy ? "renamed" : "kept";
                }

                string message = firstInstall
                    ? "Your email signature has been installed, " + employeeName + ".\n\n" +
                      "It is now the default signature for new emails, replies and forwards in Outlook. " +
                      "You can pick a different default at any time in Outlook's signature settings."
                    : "Your email signature has been updated, " + employeeName + ".\n\n" +
                      "Your default-signature choice in Outlook was kept as it was.";
                if (!dryRun && Process.GetProcessesByName("OUTLOOK").Length > 0)
                    message += "\n\nPlease close and reopen Outlook to start using it.";
                message += "\n\nBanner updates from Casterly appear automatically - you won't need to run this again " +
                           "unless your personal details change.";
                if (backup != null) message += "\n\n(Your previous signature was backed up.)";

                Report(dryRun, dryRunFolder, "OK\ndefaults=" + defaults + "\n" + message, message, MessageBoxIcon.Information);
                return 0;
            }
            catch (InstallerException ex)
            {
                Report(dryRun, dryRunFolder, "ERROR\n" + ex.Message, ex.Message, MessageBoxIcon.Warning);
                return 1;
            }
            catch (Exception ex)
            {
                string msg = "The signature could not be installed.\n\n" + ex.Message;
                Report(dryRun, dryRunFolder, "ERROR\n" + msg, msg, MessageBoxIcon.Error);
                return 2;
            }
        }

        const string BadKeyMessage =
            "This installer doesn't contain a valid signature key.\n\n" +
            "Please download it again from Signature Studio (My Signature > Install in Outlook) " +
            "and run it without renaming the file.";

        static string KeyFromFileName()
        {
            string file = Path.GetFileName(Assembly.GetExecutingAssembly().Location);
            // Strip ".exe" and the " (1)" / "(2)" that browsers add to repeated downloads,
            // in any order and any number of times (e.g. "key.exe (1).exe").
            string previous;
            do
            {
                previous = file;
                file = Regex.Replace(file, @"\.exe$", "", RegexOptions.IgnoreCase);
                file = Regex.Replace(file, @"\s*\(\d+\)$", "");
                file = file.TrimEnd();
            } while (file != previous);
            int underscore = file.IndexOf('_');
            if (underscore < 0) throw new InstallerException(BadKeyMessage);
            return file.Substring(underscore + 1);
        }

        static string FromBase64Url(string value)
        {
            string s = value.Replace('-', '+').Replace('_', '/');
            switch (s.Length % 4) { case 2: s += "=="; break; case 3: s += "="; break; }
            try { return Encoding.UTF8.GetString(Convert.FromBase64String(s)); }
            catch (FormatException) { throw new InstallerException(BadKeyMessage); }
        }

        static Dictionary<string, object> FetchSignature(string server, string employeeId, string signature)
        {
            ServicePointManager.SecurityProtocol |= (SecurityProtocolType)3072;  // TLS 1.2
            string url = server + "/api/installer/signature?e=" + Uri.EscapeDataString(employeeId) +
                         "&s=" + Uri.EscapeDataString(signature);
            var serializer = new JavaScriptSerializer { MaxJsonLength = 4 * 1024 * 1024 };
            string body;
            using (var client = new WebClient())
            {
                client.Encoding = Encoding.UTF8;
                client.Headers[HttpRequestHeader.UserAgent] = "CasterlySignatureSetup/1.0";
                try
                {
                    body = client.DownloadString(url);
                }
                catch (WebException ex)
                {
                    string serverMessage = ErrorMessageFrom(ex, serializer);
                    if (serverMessage != null) throw new InstallerException(serverMessage);
                    throw new InstallerException(
                        "Couldn't reach Signature Studio at " + server + ".\n\n" +
                        "Check your internet connection and try again.\n\n(" + ex.Message + ")");
                }
            }
            var envelope = serializer.Deserialize<Dictionary<string, object>>(body);
            if (envelope == null || !envelope.ContainsKey("data"))
                throw new InstallerException("Signature Studio sent an unexpected response.");
            return (Dictionary<string, object>)envelope["data"];
        }

        static string ErrorMessageFrom(WebException ex, JavaScriptSerializer serializer)
        {
            var response = ex.Response as HttpWebResponse;
            if (response == null) return null;
            try
            {
                using (var reader = new StreamReader(response.GetResponseStream(), Encoding.UTF8))
                {
                    var envelope = serializer.Deserialize<Dictionary<string, object>>(reader.ReadToEnd());
                    var error = (Dictionary<string, object>)envelope["error"];
                    return (string)error["message"];
                }
            }
            catch { return null; }
        }

        /// <summary>Writes Name.htm and Name.txt; returns the backup path if one was made.</summary>
        static string WriteSignatureFiles(string folder, string name, string html, string text)
        {
            Directory.CreateDirectory(folder);
            string htmPath = Path.Combine(folder, name + ".htm");
            string backup = null;
            if (File.Exists(htmPath))
            {
                // One backup of the previous version (not a new file per run).
                backup = htmPath + ".previous";
                File.Copy(htmPath, backup, true);
            }
            string document =
                "<html><head><meta http-equiv=\"Content-Type\" content=\"text/html; charset=utf-8\">" +
                "<meta name=\"Generator\" content=\"Signature Studio\"></head><body>" + html + "</body></html>";
            File.WriteAllText(htmPath, document, new UTF8Encoding(true));
            File.WriteAllText(Path.Combine(folder, name + ".txt"), text, new UTF8Encoding(true));
            return backup;
        }

        /// <summary>True when classic Outlook has at least one mail profile (i.e. has been set up).</summary>
        static bool ClassicOutlookIsSetUp()
        {
            foreach (string version in OfficeVersions)
            {
                using (RegistryKey profiles = Registry.CurrentUser.OpenSubKey(
                    @"Software\Microsoft\Office\" + version + @"\Outlook\Profiles"))
                {
                    if (profiles != null && profiles.GetSubKeyNames().Length > 0) return true;
                }
            }
            return false;
        }

        const string LegacyName = "Casterly";  // name used by earlier versions of this installer

        /// <summary>Removes an older Signature Studio signature saved as "Casterly" (only if it is ours).</summary>
        static bool RemoveLegacySignature(string folder, string newName)
        {
            if (newName == LegacyName) return false;
            string legacy = Path.Combine(folder, LegacyName + ".htm");
            if (!File.Exists(legacy) || !File.ReadAllText(legacy).Contains("content=\"Signature Studio\"")) return false;
            foreach (string suffix in new[] { ".htm", ".txt", ".htm.previous" })
            {
                string path = Path.Combine(folder, LegacyName + suffix);
                if (File.Exists(path)) File.Delete(path);
            }
            return true;
        }

        /// <summary>Where a default was the old name, switch it to the new name (other choices untouched).</summary>
        static void RepointDefaults(string oldName, string newName)
        {
            foreach (string version in OfficeVersions)
            {
                using (RegistryKey mail = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Office\" + version + @"\Common\MailSettings", true))
                {
                    if (mail == null) continue;
                    foreach (string value in new[] { "NewSignature", "ReplySignature" })
                    {
                        if (string.Equals(mail.GetValue(value) as string, oldName, StringComparison.OrdinalIgnoreCase))
                            mail.SetValue(value, newName, RegistryValueKind.String);
                    }
                }
            }
        }

        static void SetOutlookDefaults(string name)
        {
            foreach (string version in OfficeVersions)
            {
                string office = @"Software\Microsoft\Office\" + version;
                bool installed = Registry.CurrentUser.OpenSubKey(office + @"\Outlook") != null;
                if (!installed && version != "16.0") continue;

                // Default signature for new messages and for replies / forwards.
                using (RegistryKey mail = Registry.CurrentUser.CreateSubKey(office + @"\Common\MailSettings"))
                {
                    mail.SetValue("NewSignature", name, RegistryValueKind.String);
                    mail.SetValue("ReplySignature", name, RegistryValueKind.String);
                }
                // Microsoft 365 "cloud signatures" would otherwise replace the local file.
                using (RegistryKey setup = Registry.CurrentUser.CreateSubKey(office + @"\Outlook\Setup"))
                {
                    setup.SetValue("DisableRoamingSignaturesTemporaryToggle", 1, RegistryValueKind.DWord);
                }
            }
        }

        static void Report(bool dryRun, string folder, string logText, string message, MessageBoxIcon icon)
        {
            if (dryRun)
            {
                Directory.CreateDirectory(folder);
                File.WriteAllText(Path.Combine(folder, "result.txt"), logText, Encoding.UTF8);
                return;
            }
            MessageBox.Show(message, Title, MessageBoxButtons.OK, icon);
        }
    }
}
