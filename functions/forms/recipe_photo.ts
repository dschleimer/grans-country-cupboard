import { Octokit } from "octokit";
import {
  createPullRequest,
} from "octokit-plugin-create-pull-request";

import { Buffer } from "node:buffer";

const MyOctokit = Octokit.plugin(createPullRequest);

class ImgSourcePlaceholderRewriter {

    id: string;

    constructor(id) {
        this.id = id;
    }

    element(element) {
        var placeholderUrl = element.getAttribute("src");
        element.setAttribute("src", placeholderUrl.replace("999/PLACEHOLDER", this.id));
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

type TurnstileResponse = {
    success: boolean
}

const REPO_OWNER = 'dschleimer';
const REPO_NAME = 'grans-country-cupboard';
const RECIPE_IMAGE_ROOT = 'assets/recipe_photos/';
const IMAGE_EXTENSION = '.jpg';
const COMMITTER_NAME = 'David Schleimer';
const COMMITTER_EMAIL = 'dschleimer@gmail.com';

export const onRequestPost: PagesFunction<Env> = async (context) => {
    const formData = await context.request.formData();

    const token = formData.get('cf-turnstile-response');
    const ip = context.request.headers.get('CF-Connecting-IP');

    let turnstileFormData = new FormData();
        // `secret_key` here is the Turnstile Secret key, which should be set using Wrangler secrets
    formData.append('secret', context.env.TURNSTILE_SECRET_KEY);
    formData.append('response', token.toString());
    formData.append('remoteip', ip);

    const url = 'https://challenges.cloudflare.com/turnstile/v0/siteverify';
    const result = await fetch(url, {
        body: formData,
        method: 'POST',
    });

    const outcome = await result.json() as TurnstileResponse;

    if (!outcome.success) {
        // TODO: redirect back to form with error message and contents preserved as best we can
        return new Response('The provided Turnstile token was not valid!', { status: 401 });
    }
    
    const file = formData.get('photo');
    if (!(file instanceof File)) {
        //TODO: some sort of error message, and preserve the form contents as best we can
        return Response.redirect(context.request.url, 303);
    }
    //TODO: validate name/email/photo

    const fileBytes = await file.arrayBuffer();

    const authorName = formData.get('name').toString();
    const authorEmail = formData.get('email').toString();

    const recipeId = formData.get('recipe')
    const targetPath = RECIPE_IMAGE_ROOT +  recipeId + IMAGE_EXTENSION;

    //TODO: rate-limiting
    const github = new MyOctokit({
        auth: context.env.GITHUB_API_TOKEN,
    });
    try {
        var existing = await github.rest.repos.getContent({
            owner: REPO_OWNER,
            repo: REPO_NAME,
            path: targetPath,
        });
    } catch (e) {
        //TODO: some sort of error message, and preserve the form contents as best we can
        return Response.redirect(context.request.url, 303);
    }

    const now = new Date().toISOString();
    const title = "[contribution] new recipe photo for " + recipeId + " from " + authorName;
    const files = {};
    files[targetPath] = {
        content: Buffer.from(fileBytes).toString('base64'),
        encoding: "base64",
    };
    const changes = {
        emptyCommit: false,
        files: files,
        commit: title,
        author: {
            name: authorName,
            email: authorEmail,
            date: now,
        },
        committer: {
            name: COMMITTER_NAME,
            email: COMMITTER_EMAIL,
            date: now,
        }
    };

    const authorUsername = authorEmail.split('@')[0]
    const branch = 'recipe_photos-' + authorUsername + '-' + recipeId;

    var pr = await github.createPullRequest({
        owner: REPO_OWNER,
        repo: REPO_NAME,
        title: title,
        body: "",
        head: branch,
        update: true,
        createWhenEmpty: false,
        changes:[changes],
    });

    return Response.redirect(pr.data.html_url, 303);
}