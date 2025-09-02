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

export const onRequestGet: PagesFunction<Env> = async (context) => {
  var html = await context.env.ASSETS.fetch(context.request);
  var url = new URL(context.request.url);
  var id = url.searchParams.get("id");
  if (id) {
    // TODO: validate id
    return new HTMLRewriter()
        .on("img#old", new ImgSourcePlaceholderRewriter(id))
        .on("option", new SelectOptionRewriter(id))
        .transform(html);
  } else {
    return html;
  }
};