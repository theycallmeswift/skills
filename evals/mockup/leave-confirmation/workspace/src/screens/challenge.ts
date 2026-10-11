import type { Screen } from "../ui.js";

export const challengeScreen: Screen = {
  name: "challenge",
  onKey(key, station) {
    if (key.name === "escape") {
      station.goTo("attract");
    }
  },
};
