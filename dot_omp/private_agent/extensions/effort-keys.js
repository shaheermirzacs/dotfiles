import { getSupportedThinkingLevels } from "@oh-my-pi/pi-ai";

export default function (pi) {
  for (const [key, direction] of [["alt+,", -1], ["alt+.", 1]]) {
    pi.registerShortcut(key, {
      description: direction < 0 ? "Decrease effort" : "Increase effort",
      handler(ctx) {
        if (!ctx.model) return;
        const levels = getSupportedThinkingLevels(ctx.model);
        if (!levels.length) return;

        const current = levels.indexOf(pi.getThinkingLevel());
        const next = Math.max(
          0,
          Math.min(levels.length - 1, current + direction),
        );
        pi.setThinkingLevel(levels[next]);
        ctx.ui.notify(`Effort: ${pi.getThinkingLevel()}`, "info");
      },
    });
  }
}
