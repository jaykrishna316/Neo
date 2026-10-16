# Deploy Neo Landing Page to Cloudflare Pages (Free)

Cloudflare Pages offers **free static site hosting** with automatic deployments from GitHub.

## Step 1: Connect GitHub to Cloudflare

1. Go to **[dash.cloudflare.com](https://dash.cloudflare.com)**
2. Sign up or log in (free account)
3. Click **Pages** in the left sidebar
4. Click **Connect to Git**
5. Authorize Cloudflare to access your GitHub account
6. Select your repository: `jaykrishna316/codeNinja`

## Step 2: Configure Build Settings

When connecting your repository:

- **Project name**: `neo-landing` (or your choice)
- **Production branch**: `claude/conflict-warning-poc-d04y0r`
- **Framework**: None (it's a static site)
- **Build command**: (leave empty)
- **Build output directory**: (leave empty - root folder)

## Step 3: Set Environment Variables (if needed)

No environment variables needed for this static site.

## Step 4: Deploy!

1. Click **Save and Deploy**
2. Cloudflare will automatically build and deploy your site
3. Your site will be live at: `https://neo-landing.pages.dev`

## Step 5: Custom Domain (Optional)

To use your own domain:

1. Go to your Cloudflare Pages project
2. Click **Custom domains**
3. Add your domain
4. Follow DNS instructions

## Important: Image File

⚠️ **Your `neo-hero.png` image must be committed to the repository!**

Currently it's NOT in git. You need to:

```bash
# In your neoweb folder
git add neo-hero.png
git commit -m "Add hero image asset"
git push origin claude/conflict-warning-poc-d04y0r
```

Without the image committed, Cloudflare won't have it and the page won't display correctly.

## File Structure for Deployment

```
repository-root/
├── neo_premium.html          ← Main landing page
├── neo-hero.png              ← Hero image (MUST be committed!)
├── SETUP.md
├── index.html
├── README.md
└── other files...
```

## Automatic Updates

Once deployed, every time you push to `claude/conflict-warning-poc-d04y0r`:
- Cloudflare automatically redeploys
- Your live site updates within seconds
- No manual build steps needed

## DNS & Performance

Cloudflare Pages includes:
- ✅ Free SSL/HTTPS
- ✅ CDN (fast global delivery)
- ✅ Automatic backups
- ✅ Analytics dashboard
- ✅ Unlimited bandwidth

## Troubleshooting

**Page shows but image is missing?**
- Image file not committed to git
- Check filename is exactly `neo-hero.png`
- Verify it's in the repository root or same folder as HTML

**Can't see live updates?**
- Hard refresh browser (Cmd+Shift+R or Ctrl+Shift+R)
- Wait 30 seconds for CDN to clear
- Check build logs in Cloudflare dashboard

## Support

- Cloudflare Docs: https://developers.cloudflare.com/pages/
- Pages Pricing: https://pages.cloudflare.com/ (free tier listed)
