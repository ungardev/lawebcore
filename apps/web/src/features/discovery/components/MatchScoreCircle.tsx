import { cn } from '@/lib/utils';

interface MatchScoreCircleProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

export function MatchScoreCircle({ score, size = 'md', showLabel = false }: MatchScoreCircleProps) {
  const clampedScore = Math.max(0, Math.min(100, score));
  const colorClass =
    clampedScore >= 80 ? 'text-green-500' :
    clampedScore >= 60 ? 'text-yellow-500' :
    clampedScore >= 40 ? 'text-orange-500' :
    'text-red-500';

  const sizeClasses = {
    sm: 'w-10 h-10 text-sm',
    md: 'w-14 h-14 text-lg',
    lg: 'w-20 h-20 text-2xl',
  };

  const strokeWidth = size === 'sm' ? 3 : size === 'md' ? 4 : 5;
  const radius = (size === 'sm' ? 16 : size === 'md' ? 22 : 32);
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (clampedScore / 100) * circumference;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg className={sizeClasses[size]} viewBox="0 0 60 60">
        <circle
          cx="30"
          cy="30"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-muted"
        />
        <circle
          cx="30"
          cy="30"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={cn('transition-all duration-500', colorClass)}
          transform="rotate(-90 30 30)"
        />
      </svg>
      <span className={cn('absolute font-bold', sizeClasses[size], colorClass)}>
        {clampedScore}
      </span>
      {showLabel && (
        <span className="absolute -bottom-4 text-[9px] text-muted-foreground">match</span>
      )}
    </div>
  );
}
