# Deploying the app (GitHub Pages)

The app is static: `app/` builds to `app/dist`, which already contains `data/analogs_universe.json`. GitHub Pages serves it for free from this public repository. The build uses relative paths (`base: "./"` in `app/vite.config.ts`), so it works under `https://owensolis03.github.io/Space_Apps_2026_Analogos_Luna_Marte/` and under a custom domain at the root.

The workflow is [`.github/workflows/pages.yml`](../.github/workflows/pages.yml): it installs, type-checks and builds the app, then publishes it. It runs on every push to `main` and can be run by hand.

## 0. Adding the workflow file

GitHub refuses to let a token without the `workflow` permission create or change files under `.github/workflows/`, so the workflow is added in one of two ways:

- **From the web (no setup):** on GitHub, **Add file > Create new file**, name it `.github/workflows/pages.yml`, paste the content of the file of the same name from the local clone, and commit it to the branch that is being merged (or straight to `main`).
- **From the terminal:** run `gh auth refresh -h github.com -s workflow` once (it shows a code and opens the browser to approve it), then the file can be pushed like any other.

## 1. First deployment (about 5 minutes)

1. Get the code into `main` (merge the pull request). The workflow only runs from `main`, because the `github-pages` environment accepts deployments from the default branch.
2. In the repository: **Settings > Pages > Build and deployment > Source: GitHub Actions**. One time only.
3. Open the **Actions** tab. If the workflow did not start, choose "Deploy app to GitHub Pages" and **Run workflow**. A green run ends with the page URL.
4. Open `https://owensolis03.github.io/Space_Apps_2026_Analogos_Luna_Marte/` from a phone on mobile data, not from the venue Wi-Fi, and check: the map loads, the Moon and Mars buttons work, a slider reorders the list, and the site sheet opens.

To update the live app: push to `main`. To update only the data: replace `app/public/data/analogs_universe.json` and push.

## 2. Custom domain (prototerra.earth), only after step 1 works

Keep the `github.io` address as the link of record until the domain has been tested from a network outside the venue. Setting the domain before its DNS resolves makes the `github.io` address redirect to a domain that does not answer yet.

1. At the registrar (GoDaddy), from a network that allows it (for example a phone hotspot), add these DNS records for the domain:

   | Type | Name | Value |
   | --- | --- | --- |
   | A | `@` | `185.199.108.153` |
   | A | `@` | `185.199.109.153` |
   | A | `@` | `185.199.110.153` |
   | A | `@` | `185.199.111.153` |
   | CNAME | `www` | `owensolis03.github.io` |

   Remove any other A record or parking page on `@`. GitHub's own page, "Managing a custom domain for your GitHub Pages site", lists the current addresses; check it if a record is rejected.
2. Wait until `prototerra.earth` resolves to those addresses (a few minutes to a few hours).
3. **Settings > Pages > Custom domain**: enter `prototerra.earth`, save, wait for the DNS check to pass, then tick **Enforce HTTPS** (the certificate can take up to an hour or two).
4. With a GitHub Actions deployment the domain is stored in that setting; do not add a `CNAME` file.
5. Test `https://prototerra.earth` from a phone on mobile data, then put it on the project page next to the `github.io` address.

## 3. What can go wrong

| Symptom | Likely cause |
| --- | --- |
| The workflow does not appear in Actions | It is not in `main` yet |
| The deploy job fails on "environment protection" | The change was pushed from a branch other than `main` |
| The page loads but the maps are grey | The NASA tile servers (`trek.nasa.gov`, `gibs.earthdata.nasa.gov`) are blocked on that network; they work on mobile data |
| 404 on `/data/analogs_universe.json` | The build was made without `app/public/data/`; check that the file is committed |
| The domain shows a GitHub 404 | The DNS records are right but the custom domain is not saved in Settings > Pages |
