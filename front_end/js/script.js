/* ============================================================
   script.js — project renderer (path-based)
   - Edit the `PROJECTS` array below.
   - Each project: id, title, desc, thumb, color (one of the theme accents)
   - Tiles link to: /projects/<id>/
   ============================================================ */

  const root = document.documentElement;
  const toggleBtn = document.getElementById('theme-toggle');

  // Load saved theme
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme) {
    root.classList.add(savedTheme);
  }

  toggleBtn.addEventListener("click", () => {
    // Toggle the class
    if (root.classList.contains("dark")) {
      root.classList.remove("dark");
      root.classList.add("light");
      localStorage.setItem("theme", "light");
    } else {
      root.classList.remove("light");
      root.classList.add("dark");
      localStorage.setItem("theme", "dark");
    }
  });