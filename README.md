# Grans Country Cupboard

This is a technically focused document.  For non-technical users please see the [about page](about.markdown)


## Development Quickstart

This is neither the fastest nor the most complete dev setup, but it is the easiest and is sufficient to develop everything other than the dynamic bits.

1. Follow the [Jekyll installation guide](https://jekyllrb.com/docs/installation/)
1. Clone this git repo
1. cd to the root directory of your clone of this repo
1. Run `bundle install`
    * If Gemfile.lock changes please commit it and send a pull request
1. Run `bundle exec jekyll build`
    * This will be slow, about 8 minutes on my AMD 9800X3D
    * This is only needed once, with the expensive bits being cached for subsequent commands
    * See Image Handling below if you run into problems, or for alternatives
1. Run `bundle exec jekyll serve`
    * This sets up a local webserver and also builds the site as needed
    * The first cold build takes around a minute for me
    * Subsequent hot builds are around 20 seconds
    * Warnings around styles are expected, they come from the theme we're using

## Jekyll
This is a mostly-static site built using [Jekyll](jekyllrb.com) using the [jekyll][https://github.com/jekyll] /
[minima](https://github.com/jekyll/minima) theme, plus some plugins, some custom plugins and a little bit of dynamic behaviour described below.

This makes heavy use of [jekyll collections](https://jekyllrb.com/docs/collections/) both on-disk and generated via plugin.  When there is both a _foo_bar/ and foo_bar/ directory, the underscore-prefixed one contains the members of a collection, and the non-underscore prefixed directory contains an index file.

### Plugins

There are 4 custom jekyll plugins in this repo:

* book_recipe_sorting.rb which implements a custom sort-order for the book recipes, which simplifies the template logic needed to 
* categories.rb, which reads the `categories` front matter attribute of recipes and generates a categories collection with appropriate content
* ingredients.rb which parses each recipe to extract a list of ingredients, runs normalization on those ingredients, builds a collection of appropriate content, and re-writes the recipe markdown to linkify the ingredient column in the table to the appropriate ingredient collection page
* jekyll-resize-concurrent.rb see Image Handling below

## Image Handling

All images are commited only as full-resolution, under [assets/](assets/) with [_includes/img.html](_includes/img.html) being the ONLY way img tags are rendered.  Do not write your own <img /> tags and do not use the markdown image syntax.

If you need a download link, include [asset_link.html](/_includes/asset_link.html) which will generate the <a> tag for you.

### Image Taxonomy
Images are stored as assets/{type}/{id}.jpg where they are requested by type, id, and width with the appropriate width variants being generated.

### Image Types 
[original](assets/original/) and [enhanced](assets/enhanced/) are both full-page, very high-dpi scans of the cookbook.  The difference being that enhanced has had automatic sharpening and yellowing correction applied by the scanner used to digitize the cookbook.  This seemed to be a positive for the text pages but ruined the color of the cover.

[homepage](assets/homepage/) is a single image which consits of a crop of the original scan of the cover to remove the ragged edges from the photo used on the home page

[recipe_crops](assets/recipe_crops/) consist of a number of crops of the enhanced images, designed to capture everything written down for a single recipe with as little as possible of other recipes.  These are used on the pages for the individual recipes

[recipe_photos](assets/recipe_photos/) are meant to be photos of the food, as prepared by y'all.  Rather than dynamically add these as needed, I made a copy of a placeholder photo for every recipe.  This made the template logic in recipes much, much simpler.  There is tooling automatically create a pull request from an uploaded image built in to the production deployment, but feel free to send me a pull request which replaces a bnunch of these in a single commit.  

### Image IDs
`original` and `enhanced` use the page number from the cookbook 0-padded to 3 digits, with special cases for the un-numbered `cover` and `title` pages.

`homepage` uses `cover` as the single id.

`recipe_crops` and `recipe_photos` use NNN/recipe_name where NNN is the 0-padded 3-digit page number, and recipe_name is the lower_snake_case name of the recipe.  This both matches the layout of recipes under _book_recipes and is also the value of the recipe: front-matter attribute with the latter being authoritative.  I've been meaning to write a plugin or something to avoid the duplication but haven't had time.

### Image Widths
We use 3 image widths, with the heights being automatic, preserving the original images aspect ratio:
* Thumbnails are 100px wide
* Half-Column images (recipe crops and food photos) are 395px wide
* Full-Column images (page scans, homepage, etc) are 800 px wide
* Originals are, well, the original size

The column widths come from the jekyll-minima plugin which sets the max width for content to 800px, allowing 10px of padding between two half-width images.

If you add a new, widely used width/type combination please add it to [_plugins/jekyll-resize-concurrent.rb](_plugins/jekyll-resize-concurrent.rb)

These widths are specified as numbers at the include location for `img.html` rather than constants.

### Production

We use [Cloudflare's Images product](https://developers.cloudflare.com/images/) to resize and serve images in production.  There is a github action which uploads the contents of [assets](assets/) to a [Cloudflare R2](https://developers.cloudflare.com/r2/) bucket which is configred to serve from https://assets.grans-country-cupboard.com with Images also configured on that domain.  [_includes/img.html](_includes/img.html) contains the logic for generating a URL which instructs Cloudflare to resize the image to an appropriate width and adjust the image format the browser loading the page.  It will also be automatically cached in the cloudflare CDN.

This fits in the cloudlfare free tier for both R2 and Images, barely.

### Development

We use a fork of a fork of the jekyll-resize image plugin, combined with a local plugin for just this repository.  The [Original Plugin](https://github.com/CloudCannon/jekyll-resize/) got abandoned and [forked for Current Jekyll](https://github.com/MichaelCurrin/jekyll-resize) which I then forked again to trade off more space usage in the cache for *much* faster builds.

By default this repo is configured to use [_plugins/jekyll-resize-concurrent.rb](_plugins/jekyll-resize-concurrent.rb) and the [jekyll-resize plugin](https://github.com/dschleimer/jekyll-resize) from my github via [Gemfile](Gemfile.rb) and [_config.yml](_config.yml).

`jekyll-resize` provides a liquid filter `resize` which both generates the resizes when needed, and outputs the appropriate url for the resized image.  The `img.html` include file uses this appropriately.

The upstream version of `jekyll-resize` uses a hash of the contents of it's input files as a file name within the cache to determine whether an image needs to be resized or not.  This saves space when you have duplicate images (which we do) but costs time, because you need to read and compute the hash of every input file every time you regenerate a given page.  This took 30+ minutes for an empty-cache build and 3+ minutes for a no-op change with a full cache and a hot `jekyll serve`.

My fork changes `jekyll-resize` to use the file name of the source instead of the hash in the cache paths, and to use file modification times to determine whether to rebuild.  In addition, the `jekyll-resize-concurrent` plugin local to this repo invokes the `resize` filter for the widely-used type/width combinations concurrently using 2 * NUM_CPUS threads.  If you need to slow this down, you can either change the constants in the file for a single run, or send me a pull request to make it configuration driven.  I have enough ram to run as many ImageMagick jobs as I need in parallel, but not everyone does.

### Hybrid

If you aren't making any changes to images, you can use a hybrid setup where the html/css/js are served locally, but images are served from the production cloudflare deployment.  This will give the fastest development loop, and also use the least disk space.  It's really easy to get confused when you change something, see the regeneration happen and reload but see the old image though.  From personal experience.

Windows in Powershell:
```pwsh
$env:JEKYLL_ENV="production" # note this sets it for every subsequent run in a given terminal
bundle exec jekyll serve --config _config.yml,_config_prod.yml
```

Linux/MacOS in bash:
```bash
# this will set the env variable for only a single run
JEKYLL_ENV=production bundle exec jekyll serve --config _config.yml,_config_prod.yml
# this will set it for every subsequent run in a given terminal
export JEKYLL_ENV=production
bundle exec jekyll serve --config _config.yml,_config_prod.yml
```

The `JEKYLL_ENV` variable configures the include to use the production image urls, and the config file bit excludes the images fomr the jekyll build, which prevents the concurrent resize from running.

## Dynamic Content

Aside from image resizing, the only non-static bit of this website is the bit which allows folks to upload recipe photos, and which creates a pull request using the uploaded image.

This is implemented using the [Cloudflare Pages Function](https://developers.cloudflare.com/pages/functions/) feature.

We have a Jekyll template under [forms/](forms) and typescript under [functions/forms](functions/forms) at the same path, which work together.  During the build, cloudflare both compiles the jekyll template into a "static file" and builds the functions into a js bundle, set up to run against requests with the `functions/` path prefix removed.  If you have the same path in both static and functions, the functions one will win but can access the contents of the static file.

This is exactly what we do for the image upload form.  When a GET request is made for that path, the TS runs, loads the static content, runs a couple replacements based on url parameters, and then returns the rendered HTML to the browser.

When a POST request is made against the path in question, the TS runs to accept the uploaded image and other form data.  It uses that to create a pull request replacing the appropriate image file via github API.

The dev env setup here requires access to my github and cloudflare accounts, so it's beyond the scope of this readme.

Al please delete this line.