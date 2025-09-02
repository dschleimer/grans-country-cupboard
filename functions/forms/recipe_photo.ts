import { Octokit } from "octokit";
import {
  createPullRequest,
} from "octokit-plugin-create-pull-request";

const MyOctokit = Octokit.plugin(createPullRequest);

class ImgSourcePlaceholderRewriter {

    id: string;

    constructor(id) {
        this.id = id;
    }

    element(element) {
        var placeholderUrl = element.getAttribute("src");
        element.setAttribute("src", placeholderUrl.replace("$$RECIPE_PAGE/RECIPE_NAME$$", this.id));
    }

    comments(comment) {}
    text(text) {}
}

class SelectOptionRewriter {
        id: string;

    constructor(id) {
        this.id = id;
    }

    element(element) {
        if (element.getAttribute("value") == this.id ) {
            element.setAttribute("selected", true);
        }
    }

    comments(comment) {}
    text(text) {}
}

class FormActionRewriter {
    url: URL;

    constructor(url) {
        this.url = url;
    }

    element(element) {
        element.setAttribute("action", this.url.href);
    }

    comments(comment) {}
    text(text) {}
}

export const onRequestGet: PagesFunction<Env> = async (context) => {
    var html = await context.env.ASSETS.fetch(context.request);
    var url = new URL(context.request.url);
    var id = url.searchParams.get("id");
    var recipe = null;
    if (id) {
        try {
            recipe = await context.env.ASSETS.fetch(new URL("/book_recipes/" + id, url ))
            if (!recipe.ok) {
                console.log("Got status code %d (%s) while trying to lookup recipe id %s", recipe.status, recipe.statusText, id);
            }
        } catch (error) {
            console.error("Error while generating recipe photo form for invalid recipe ID: %s", id, error);
        }
    }
    if (recipe && recipe.ok) {
        return new HTMLRewriter()
            .on("img#old", new ImgSourcePlaceholderRewriter(id))
            .on("option", new SelectOptionRewriter(id))
            .on("form", new FormActionRewriter(url))
            .transform(html);
    } else {
        return html;
    }
};

const REPO_OWNER = 'dschleimer';
const REPO_NAME = 'grans-country-cupboard';
const RECIPE_IMAGE_ROOT = '/assets/recipe_photos/';
const IMAGE_EXTENSION = '.jpg';

export const onRequestPost: PagesFunction<Env> = async (context) => {
    const formData = await context.request.formData();
    console.log(formData);
    const file = formData.get('photo');
    console.log(file);
    if (!(file instanceof File)) {
        //TODO: some sort of error message, and preserve the form contents as best we can
        return Response.redirect(context.request.url, 303);
    }
    //TODO: validate name/email/photo

    const recipeId = formData.get('recipe')
    const targetPath = RECIPE_IMAGE_ROOT +  recipeId + IMAGE_EXTENSION;

    const github = new MyOctokit({
        auth: context.env.GITHUB_API_TOKEN,
    });
    try {
        var existing = await github.rest.repos.getContent({
            owner: 'dschleimer',
            repo: 'grans-country-cupboard',
            path: targetPath,
        });
    } catch (e) {
        //TODO: some sort of error message, and preserve the form contents as best we can
        return Response.redirect(context.request.url, 303);
    }
    return new Response(JSON.stringify(existing, null, 4));
};