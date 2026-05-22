/**
 * Fix-13/12 — single source of truth for licence-related URLs that
 * are duplicated across the desktop app's UI.
 *
 * The site bundle (``apps/site``) has its own copy of this constant
 * in ``apps/site/src/lib/licenseApi.ts`` — keeping the value in two
 * separate bundles is intentional: each bundle is shipped to a
 * different surface (Electron / Pages) and we don't want a runtime
 * import dependency between them. Tests assert both copies agree.
 */
export const LEMON_SQUEEZY_CHECKOUT_URL =
  'https://research-assistant.lemonsqueezy.com/buy/REPLACE-AFTER-LS-PRODUCT-CREATED'
