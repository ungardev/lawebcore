import { cn } from '@/lib/utils';

type CountryCode = string;

interface CountryFlagProps {
  countryCode: CountryCode;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeMap = {
  sm: 20,
  md: 24,
  lg: 32,
};

const veSvg = (size: number) => `
  <svg width="${size}" height="${Math.round(size * 2 / 3)}" viewBox="0 0 30 20" xmlns="http://www.w3.org/2000/svg">
    <rect width="30" height="20" fill="#FFE033"/>
    <rect y="7" width="30" height="6" fill="#0050DD"/>
    <rect y="13" width="30" height="7" fill="#DA1212"/>
    <path d="M15 5.5 Q 12.5 8 15 10 Q 17.5 8 15 5.5Z" fill="#FFE033"/>
    <circle cx="15" cy="7.5" r="1.2" fill="#FFE033"/>
  </svg>
`;

const veFallbackSvg = (size: number) => `
  <svg width="${size}" height="${Math.round(size * 2 / 3)}" viewBox="0 0 30 20" xmlns="http://www.w3.org/2000/svg">
    <rect width="30" height="20" fill="#FFE033"/>
    <rect y="7" width="30" height="6" fill="#0050DD"/>
    <rect y="13" width="30" height="7" fill="#DA1212"/>
  </svg>
`;

const flagRegistry: Record<string, (size: number) => string> = {
  VE: veSvg,
};

const fallbackFlagSvg = (size: number) => `
  <svg width="${size}" height="${Math.round(size * 2 / 3)}" viewBox="0 0 30 20" xmlns="http://www.w3.org/2000/svg">
    <rect width="30" height="20" fill="#9CA3AF"/>
    <text x="15" y="14" text-anchor="middle" font-size="8" fill="white" font-weight="bold">${'??'}</text>
  </svg>
`;

export function CountryFlag({ countryCode, size = 'md', className }: CountryFlagProps) {
  const pixelSize = sizeMap[size];
  const code = countryCode.toUpperCase();
  const svgFn = flagRegistry[code];
  const svgContent = svgFn ? svgFn(pixelSize) : fallbackFlagSvg(pixelSize);

  return (
    <span
      className={cn('inline-flex items-center justify-center shrink-0', className)}
      dangerouslySetInnerHTML={{ __html: svgContent }}
      title={countryCode}
      aria-label={countryCode}
    />
  );
}
