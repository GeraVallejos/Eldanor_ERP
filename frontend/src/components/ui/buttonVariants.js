import { cn } from '@/lib/utils'

const VARIANT_STYLES = {
  default: 'bg-primary text-primary-foreground hover:brightness-95',
  outline: 'border border-border bg-transparent text-foreground hover:bg-muted',
  ghost: 'text-foreground hover:bg-muted',
}

const SIZE_STYLES = {
  sm: 'h-8 px-3 text-xs',
  md: 'h-9 px-4 text-sm',
  lg: 'h-10 px-5 text-sm',
}

export function buttonVariants({ variant = 'default', size = 'md', fullWidth = false } = {}) {
  return cn(
    'inline-flex items-center justify-center rounded-md font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60',
    VARIANT_STYLES[variant] || VARIANT_STYLES.default,
    SIZE_STYLES[size] || SIZE_STYLES.md,
    fullWidth && 'w-full',
  )
}
