/** Shared motion presets — spring-first, calm, premium feel */
export const motionSpring = {
  gentle: { damping: 22, stiffness: 180, mass: 0.8 },
  snappy: { damping: 18, stiffness: 260, mass: 0.7 },
  card: { damping: 20, stiffness: 200, mass: 0.85 },
} as const;

export const staggerMs = 70;
