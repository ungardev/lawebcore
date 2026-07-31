import { cn } from '@/lib/utils';
import type { Platform } from '../types/discovery';

interface PlatformIconProps {
  platform: Platform;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const sizeMap = {
  sm: 16,
  md: 20,
  lg: 24,
};

const instagramSvg = (size: number) => `
  <svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <linearGradient id="ig-grad" x1="0%" y1="100%" x2="100%" y2="0%">
        <stop offset="0%" style="stop-color:#FFDC80"/>
        <stop offset="25%" style="stop-color:#F56040"/>
        <stop offset="50%" style="stop-color:#F77737"/>
        <stop offset="75%" style="stop-color:#F05347"/>
        <stop offset="100%" style="stop-color:#C13584"/>
      </linearGradient>
    </defs>
    <rect x="2" y="2" width="20" height="20" rx="5" stroke="url(#ig-grad)" stroke-width="2" fill="none"/>
    <circle cx="12" cy="12" r="5" stroke="url(#ig-grad)" stroke-width="2" fill="none"/>
    <circle cx="17.5" cy="6.5" r="1" fill="url(#ig-grad)"/>
  </svg>
`;

const tiktokSvg = (size: number) => `
  <svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-2.88 2.5 2.89 2.89 0 01-2.89-2.89 2.89 2.89 0 012.89-2.89c.28 0 .54.04.79.1V9.01a6.33 6.33 0 00-.79-.05 6.34 6.34 0 00-6.34 6.34 6.34 6.34 0 006.34 6.34 6.34 6.34 0 006.33-6.34V8.69a8.27 8.27 0 004.84 1.55V6.79a4.85 4.85 0 01-1.07-.1z" fill="#010101"/>
  </svg>
`;

const youtubeSvg = (size: number) => `
  <svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="24" height="24" rx="4" fill="#FF0000"/>
    <path d="M16.18 12L10 8.55V15.45L16.18 12Z" fill="white"/>
  </svg>
`;

const xSvg = (size: number) => `
  <svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="24" height="24" rx="4" fill="#000000"/>
    <path d="M17.5 7L13.5 11.5L17.5 16H15L12 12.5L9 16H6.5L10.5 11.5L6.5 7H9L12 10.5L15 7H17.5Z" fill="white"/>
  </svg>
`;

const facebookSvg = (size: number) => `
  <svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="24" height="24" rx="4" fill="#1877F2"/>
    <path d="M13 9.5H15.5L16.5 6H13V4.5C13 3.67 13.67 3 14.5 3H16.5V0.5C16.5 0.5 15.67 0.5 15 0.5C13.33 0.5 12 1.67 12 3.5V6H10V9.5H12V18H15V9.5Z" fill="white"/>
  </svg>
`;

const fallbackSvg = (size: number) => `
  <svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
    <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
    <path d="M12 8v4M12 16h.01" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
  </svg>
`;

export function PlatformIcon({ platform, size = 'md', className }: PlatformIconProps) {
  const pixelSize = sizeMap[size];
  let svgContent: string;

  switch (platform) {
    case 'instagram':
      svgContent = instagramSvg(pixelSize);
      break;
    case 'tiktok':
      svgContent = tiktokSvg(pixelSize);
      break;
    case 'youtube':
      svgContent = youtubeSvg(pixelSize);
      break;
    case 'x':
      svgContent = xSvg(pixelSize);
      break;
    case 'facebook':
      svgContent = facebookSvg(pixelSize);
      break;
    default:
      svgContent = fallbackSvg(pixelSize);
  }

  return (
    <span
      className={cn('inline-flex items-center justify-center shrink-0', className)}
      dangerouslySetInnerHTML={{ __html: svgContent }}
      aria-label={platform}
    />
  );
}
