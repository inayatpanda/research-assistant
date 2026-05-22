// Phase L1a — Email send wrapper. Uses Resend's REST API directly (lighter
// than the SDK) so the Worker bundle stays small. The interface is small
// enough to mock in tests via dependency injection.

export interface SendEmailArgs {
  to: string;
  subject: string;
  html: string;
  text: string;
}

export interface SendEmailResult {
  ok: boolean;
  id?: string;
  error?: string;
}

export interface EmailSender {
  send(args: SendEmailArgs): Promise<SendEmailResult>;
}

export class ResendEmailSender implements EmailSender {
  constructor(
    private readonly apiKey: string,
    private readonly from: string,
  ) {}

  async send(args: SendEmailArgs): Promise<SendEmailResult> {
    if (!this.apiKey) {
      return { ok: false, error: "RESEND_API_KEY not configured" };
    }
    try {
      const resp = await fetch("https://api.resend.com/emails", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${this.apiKey}`,
        },
        body: JSON.stringify({
          from: this.from,
          to: [args.to],
          subject: args.subject,
          html: args.html,
          text: args.text,
        }),
      });
      const body = (await resp.json().catch(() => null)) as {
        id?: string;
        message?: string;
      } | null;
      if (!resp.ok) {
        return { ok: false, error: body?.message ?? `Resend HTTP ${resp.status}` };
      }
      return { ok: true, id: body?.id };
    } catch (err) {
      return { ok: false, error: (err as Error).message };
    }
  }
}

/** Drops emails on the floor. Used in tests and when RESEND_API_KEY is unset. */
export class NullEmailSender implements EmailSender {
  public readonly sent: SendEmailArgs[] = [];
  async send(args: SendEmailArgs): Promise<SendEmailResult> {
    this.sent.push(args);
    return { ok: true, id: `null-${this.sent.length}` };
  }
}

// ---------- templates -------------------------------------------------

function shell(name: string, body: string, ctaUrl: string, ctaLabel: string): string {
  return `<!doctype html><html><body style="font-family:-apple-system,Segoe UI,sans-serif;color:#0f172a;line-height:1.55;padding:24px;max-width:560px;margin:auto">
<h1 style="font-size:20px;margin-bottom:8px">Hi ${escapeHtml(name)},</h1>
${body}
<p style="margin-top:24px"><a href="${escapeHtml(ctaUrl)}" style="display:inline-block;padding:10px 18px;background:#0f172a;color:#fff;border-radius:6px;text-decoration:none">${escapeHtml(ctaLabel)}</a></p>
<p style="color:#64748b;font-size:13px;margin-top:24px">— The Research Assistant team</p>
</body></html>`;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export interface WelcomeTrialArgs {
  display_name: string;
  trial_days: number;
  download_url: string;
}

export function welcomeTrialEmail(args: WelcomeTrialArgs): { subject: string; html: string; text: string } {
  const subject = `Your Research Assistant trial is active (${args.trial_days} days)`;
  const body = `<p>Your free trial is active for <strong>${args.trial_days} days</strong>. Download the desktop app to get started.</p>`;
  return {
    subject,
    html: shell(args.display_name, body, args.download_url, "Download the app"),
    text: `Hi ${args.display_name},\n\nYour ${args.trial_days}-day trial is active. Download the app: ${args.download_url}\n\n— Research Assistant`,
  };
}

export interface WelcomeLifetimeArgs {
  display_name: string;
  temp_password: string;
  login_url: string;
}

export function welcomeLifetimeEmail(args: WelcomeLifetimeArgs): { subject: string; html: string; text: string } {
  const subject = `Welcome to Research Assistant — your lifetime licence is ready`;
  const body = `<p>Thanks for purchasing the lifetime version. We've created an account for you.</p>
  <p><strong>Temporary password:</strong> <code style="background:#f1f5f9;padding:2px 6px;border-radius:4px">${escapeHtml(args.temp_password)}</code></p>
  <p>Sign in and change it from the account screen.</p>`;
  return {
    subject,
    html: shell(args.display_name, body, args.login_url, "Sign in"),
    text: `Hi ${args.display_name},\n\nThanks for purchasing the lifetime version.\n\nTemporary password: ${args.temp_password}\n\nSign in: ${args.login_url}\n\n— Research Assistant`,
  };
}

export interface PurchaseConfirmationArgs {
  display_name: string;
  login_url: string;
}

export function purchaseConfirmationEmail(args: PurchaseConfirmationArgs): { subject: string; html: string; text: string } {
  const subject = `Thanks for purchasing Research Assistant`;
  const body = `<p>Your account has been upgraded to the lifetime version. Thanks for your support.</p>`;
  return {
    subject,
    html: shell(args.display_name, body, args.login_url, "Open the app"),
    text: `Hi ${args.display_name},\n\nThanks for purchasing the lifetime version. Your account is now upgraded.\n\n${args.login_url}\n\n— Research Assistant`,
  };
}

export interface PasswordResetArgs {
  display_name: string;
  reset_url: string;
  ttl_minutes: number;
}

export function passwordResetEmail(args: PasswordResetArgs): { subject: string; html: string; text: string } {
  const subject = `Reset your Research Assistant password`;
  const body = `<p>You asked to reset your password. The link below expires in <strong>${args.ttl_minutes} minutes</strong>. If you didn't request this, you can ignore this email.</p>`;
  return {
    subject,
    html: shell(args.display_name, body, args.reset_url, "Reset password"),
    text: `Hi ${args.display_name},\n\nReset your password: ${args.reset_url}\n(Expires in ${args.ttl_minutes} minutes.)\n\n— Research Assistant`,
  };
}
