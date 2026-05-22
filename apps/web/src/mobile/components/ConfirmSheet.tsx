/**
 * Fix-13/9 — ConfirmSheet.
 *
 * Mobile-friendly replacement for ``window.confirm``. Native confirm
 * dialogs are unreliable in iOS PWAs — they can be silently
 * suppressed when the page isn't the active tab, can break swipe-back
 * gestures, and look totally out of place against the rest of the
 * mobile UI.
 *
 * Wraps the ``BottomSheet`` primitive with a title, message, primary
 * (destructive by default) button, and a cancel button. Returns ``void``;
 * callers wire ``onConfirm`` + ``onCancel`` handlers instead of awaiting
 * a boolean — the API matches a Radix-style controlled component, not
 * a procedural confirm() call.
 */
import { Button } from '@/components/ui/button'
import { BottomSheet } from './BottomSheet'

export interface ConfirmSheetProps {
  open: boolean
  /** Sheet title (also doubles as the screen-reader label). */
  title: string
  /** Body copy; usually a one-liner explaining what will happen. */
  message: string
  /** Confirm-button text. Defaults to "Delete" for destructive flows. */
  confirmLabel?: string
  /** Cancel-button text. Defaults to "Cancel". */
  cancelLabel?: string
  /** When ``true`` the confirm button uses a destructive (rose) style. */
  destructive?: boolean
  /** Fires when the user taps Confirm. */
  onConfirm(): void
  /** Fires when the user taps Cancel, the backdrop or Escape. */
  onCancel(): void
}

export function ConfirmSheet({
  open,
  title,
  message,
  confirmLabel = 'Delete',
  cancelLabel = 'Cancel',
  destructive = true,
  onConfirm,
  onCancel,
}: ConfirmSheetProps) {
  return (
    <BottomSheet
      open={open}
      onClose={onCancel}
      title={title}
      snapPoints={['auto', '40%']}
      defaultSnap={0}
    >
      <div data-testid="confirm-sheet" className="space-y-4 pt-1">
        <p className="text-[14px] text-muted-foreground">{message}</p>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            className="flex-1"
            onClick={onCancel}
            data-testid="confirm-sheet-cancel"
          >
            {cancelLabel}
          </Button>
          <Button
            type="button"
            variant={destructive ? 'destructive' : 'default'}
            className="flex-1"
            onClick={onConfirm}
            data-testid="confirm-sheet-confirm"
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </BottomSheet>
  )
}
