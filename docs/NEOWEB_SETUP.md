# Setup Private neoweb Repo + Cloudflare Hosting

Your private repo is ready: https://github.com/jaykrishna316/neoweb

## Step 1: Clone Your Private Repo (Local)

On your Mac, in Terminal:

```bash
git clone https://github.com/jaykrishna316/neoweb.git
cd neoweb
```

## Step 2: Add Your Landing Page Files

Copy your files into the neoweb folder:

```bash
# From your Desktop
cp ~/Desktop/neoweb/neo_premium.html .
cp ~/Desktop/neoweb/neo-hero.png .
```

## Step 3: Commit and Push to Private Repo

```bash
git add neo_premium.html neo-hero.png
git commit -m "Add Neo landing page with hero image"
git push origin main
```

## Step 4: Connect Private Repo to Cloudflare Pages

1. Go to **[dash.cloudflare.com](https://dash.cloudflare.com)**
2. Click **Pages** → **Connect to Git**
3. Authorize Cloudflare
4. Select your repo: `jaykrishna316/neoweb`
5. Production branch: `main`
6. Framework: None (leave empty)
7. Build command: (leave empty)
8. Build output directory: (leave empty)
9. Click **Save and Deploy** ✨

## Result

- ✅ Your code stays in **private GitHub repo**
- ✅ Only you can see the code
- ✅ Cloudflare hosts it publicly at: `https://neoweb.pages.dev`
- ✅ Every push to GitHub = automatic Cloudflare deployment
- ✅ No code in public Neo repo

## Future Updates

After initial setup, just:

```bash
cd ~/neoweb
# Make changes to neo_premium.html or neo-hero.png
git add .
git commit -m "Update description"
git push origin main
# Cloudflare auto-deploys within seconds
```

## Check Deployment Status

- Cloudflare Dashboard: Shows build progress and live site
- Your site: `https://neoweb.pages.dev/neo_premium.html`

## Important Notes

- Keep your private repo **Private** (not Public)
- Never commit sensitive data
- Image file `neo-hero.png` must be in repo for Cloudflare to have it
- File structure should be:
  ```
  neoweb/
  ├── neo_premium.html
  ├── neo-hero.png
  └── README.md (optional)
  ```

Done! Your landing page is now private but publicly hosted on Cloudflare. 🚀
