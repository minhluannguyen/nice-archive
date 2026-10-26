# NICE Archive website

This directory contains the Hugo site source, the Book theme, and generated site files. The documentation text stays in the repository's `docs/` directory and is mounted by `hugo.toml`.

From the repository root, build the site with:

```sh
nix develop .#docs -c bash -c 'cd web && hugo --cleanDestinationDir'
```

The result is written to `web/public/`. To preview it locally, run:

```sh
nix develop .#docs -c bash -c 'cd web && hugo server --renderToMemory'
```

Open the URL printed by Hugo, normally `http://localhost:1313/`. The development configuration uses `/` for local previews; production builds still use the GitHub Pages `/nice-archive/` path.

`layouts/_partials/docs/menu-filetree.html` replaces the theme's automatic file-tree sidebar with the menu in `hugo.toml`. `layouts/_partials/docs/links/portable-link.html` resolves links to published pages and sends links to repository source files to GitHub.
