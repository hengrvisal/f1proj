/** F1 team colors for visualization */
export const TEAM_COLORS: Record<string, string> = {
  "Red Bull Racing": "#3671C6",
  "Red Bull": "#3671C6",
  "Ferrari": "#E8002D",
  "Scuderia Ferrari": "#E8002D",
  "Mercedes": "#27F4D2",
  "McLaren": "#FF8000",
  "Aston Martin": "#229971",
  "Alpine F1 Team": "#FF87BC",
  "Alpine": "#FF87BC",
  "Williams": "#64C4FF",
  "AlphaTauri": "#6692FF",
  "RB F1 Team": "#6692FF",
  "Kick Sauber": "#52E252",
  "Alfa Romeo": "#C92D4B",
  "Haas F1 Team": "#B6BABD",
  "Haas": "#B6BABD",
};

export const CLUSTER_COLORS = [
  "#E10600", "#00D2BE", "#FF8700", "#0090FF", "#B14BA7",
  "#2D826D", "#F596C8",
];

export const COMPOUND_COLORS: Record<string, string> = {
  SOFT: "#FF3333",
  MEDIUM: "#FFDD00",
  HARD: "#EEEEEE",
  INTERMEDIATE: "#43B02A",
  WET: "#0067AD",
};

export function getTeamColor(team: string): string {
  for (const [key, color] of Object.entries(TEAM_COLORS)) {
    if (team.toLowerCase().includes(key.toLowerCase()) || key.toLowerCase().includes(team.toLowerCase())) {
      return color;
    }
  }
  return "#888899";
}
