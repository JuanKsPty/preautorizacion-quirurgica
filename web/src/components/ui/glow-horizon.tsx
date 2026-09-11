"use client";

import { motion } from 'framer-motion';

const EASE = [0.16, 1, 0.3, 1] as const;
const DURATION = 2;

export type GlowHorizonVariant = 'top' | 'bottom' | 'left' | 'right';

const VARIANTS: Record<GlowHorizonVariant, { axis: 'x' | 'y'; scaleAxis: 'scaleX' | 'scaleY'; enterPct: string; restPct: string }> = {
  top: { axis: 'y', scaleAxis: 'scaleY', enterPct: '-100%', restPct: '-50%' },
  bottom: { axis: 'y', scaleAxis: 'scaleY', enterPct: '100%', restPct: '50%' },
  left: { axis: 'x', scaleAxis: 'scaleX', enterPct: '100%', restPct: '50%' },
  right: { axis: 'x', scaleAxis: 'scaleX', enterPct: '-100%', restPct: '-50%' },
};

export interface GlowHorizonProps {
  className?: string;
  variant?: GlowHorizonVariant;
}

export default function GlowHorizonFM({ className, variant = 'top' }: GlowHorizonProps) {
  const { axis, scaleAxis, enterPct, restPct } = VARIANTS[variant];

  return (
    <motion.div
      className={'absolute h-full w-full ' + (className ?? '')}
      style={{ isolation: 'isolate' }}
      initial={{ [axis]: enterPct, [scaleAxis]: 1.5, opacity: 0, filter: 'blur(15px)' }}
      animate={{ [axis]: restPct, [scaleAxis]: 1, opacity: 1, filter: 'blur(0px)' }}
      transition={{ duration: DURATION, ease: EASE }}
    >
      <Arc variant={variant} color="var(--glow-highlight)" size="132%" boxShadow="var(--glow-shadow)" delay={1.2} />
      <Arc variant={variant} color="var(--glow-mist)" size="120%" initialOffset="10%" blur={31} delay={0.6} />
      <Arc variant={variant} color="var(--glow-core)" size="124%" initialOffset="10%" blur={21} delay={0} />
      <Arc variant={variant} color="var(--glow-shadow-core)" size="120%" initialOffset="10%" blur={51} delay={0} />
    </motion.div>
  );
}

function Arc({ variant, color, size, initialOffset, blur, boxShadow, delay }: {
  variant: GlowHorizonVariant;
  color: string;
  size: string;
  initialOffset?: string;
  blur?: number;
  boxShadow?: string;
  delay: number;
}) {
  const scale = parseFloat(size) / 100;
  const { axis, enterPct } = VARIANTS[variant];
  const sign = enterPct.startsWith('-') ? -1 : 1;
  const startPct = initialOffset ? `${sign * Math.abs(parseFloat(initialOffset) - 50)}%` : undefined;

  return (
    <motion.div
      aria-hidden
      className="absolute inset-0 rounded-[100%]"
      style={{
        scale,
        background: color,
        transition: 'background 500ms ease, box-shadow 500ms ease',
        ...(blur !== undefined && { filter: `blur(${blur}px)` }),
        ...(boxShadow && { boxShadow }),
      }}
      initial={startPct ? { [axis]: startPct } : false}
      animate={startPct ? { [axis]: 0 } : undefined}
      transition={{ duration: DURATION, ease: EASE, delay }}
    />
  );
}
