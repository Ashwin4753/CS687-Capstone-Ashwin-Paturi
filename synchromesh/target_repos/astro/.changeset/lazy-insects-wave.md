---
'astro': minor
---

Removes redundant `fetchpriority` attributes from the output of Astro’s `<Image>` component

Previously, Astro would always include `fetchpriority="auto"` on images not using the `priority` attribute.
However, this is the default value, so specifying it is redundant. This change omits the attribute by default.
