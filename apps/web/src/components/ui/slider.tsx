import * as React from 'react';
import { cn } from '@/lib/utils';

export interface SliderProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type' | 'value' | 'defaultValue'> {
  value?: number;
  defaultValue?: number;
}

const Slider = React.forwardRef<HTMLInputElement, SliderProps>(({ className, value, defaultValue, ...props }, ref) => (
  <input
    ref={ref}
    type="range"
    value={value}
    defaultValue={defaultValue}
    className={cn('h-2 w-full cursor-pointer appearance-none rounded-full bg-surface-raised accent-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background', className)}
    {...props}
  />
));
Slider.displayName = 'Slider';

export { Slider };
