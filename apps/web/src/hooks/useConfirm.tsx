import { useState, useCallback, useRef } from 'react';
import { ConfirmDialog, type ConfirmDialogVariant } from '@/components/ui/dialog';

export interface ConfirmOptions {
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: ConfirmDialogVariant;
}

export function useConfirm() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [options, setOptions] = useState<ConfirmOptions | null>(null);
  const resolveRef = useRef<((value: boolean) => void) | null>(null);

  const confirm = useCallback((opts: ConfirmOptions): Promise<boolean> => {
    setOptions(opts);
    setDialogOpen(true);
    return new Promise<boolean>((resolve) => {
      resolveRef.current = resolve;
    });
  }, []);

  const handleConfirm = useCallback(() => {
    resolveRef.current?.(true);
    resolveRef.current = null;
    setDialogOpen(false);
    setOptions(null);
  }, []);

  const handleCancel = useCallback(() => {
    resolveRef.current?.(false);
    resolveRef.current = null;
    setDialogOpen(false);
    setOptions(null);
  }, []);

  const ConfirmDialogComponent = options ? (
    <ConfirmDialog
      open={dialogOpen}
      onOpenChange={(open) => {
        if (!open) handleCancel();
      }}
      title={options.title}
      description={options.description}
      confirmLabel={options.confirmLabel}
      cancelLabel={options.cancelLabel}
      variant={options.variant}
      onConfirm={handleConfirm}
      onCancel={handleCancel}
    />
  ) : null;

  return [ConfirmDialogComponent, confirm] as const;
}
