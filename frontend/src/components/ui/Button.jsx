import { forwardRef } from 'react'
import { buttonVariants } from '@/components/ui/buttonVariants'
import { cn } from '@/lib/utils'

const Button = forwardRef(function Button(
  { className, variant = 'default', size = 'md', fullWidth = false, type = 'button', ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(buttonVariants({ variant, size, fullWidth }), className)}
      {...props}
    />
  )
})

export default Button
