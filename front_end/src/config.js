//export const BACKEND_URL = "http://0.0.0.0:5000";
export const BACKEND_URL = "https://w101-40217740204.us-west1.run.app";

export const TARGET_PATH  = "/static/w101/icons/battle/targets/";

export const BATTLE_PATH = "/static/w101/icons/battle/";

export const goodColor = "green";
export const badColor = "red";

export const SCHOOLS = ["fire", "ice", "storm", "life", "death", "myth", "balance"];

export function pipSrc(pip_type) {
  if (pip_type === "regular") return BACKEND_URL + BATTLE_PATH + "pips/Pip.png";
  if (pip_type === "powerpip") return BACKEND_URL + BATTLE_PATH + "pips/Power_Pip.png";
  //Otherwise, it is a school pip:
  const title = pip_type.charAt(0).toUpperCase() + pip_type.slice(1);
  return BACKEND_URL + BATTLE_PATH + `pips/${title}_School_Pip.png`;
}