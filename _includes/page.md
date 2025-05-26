---
---

{%unless page.number == "cover" %}
    {%assign suffix = "_enhanced" %}
{%else%}
    {% assign suffix = "" %}
{%endunless%}

{%capture web%}/assets/web/cookbook_{{page.number}}{{suffix}}.jpg{%endcapture%}
{%capture orig%}/assets/full_res/cookbook_{{page.number}}.jpg{%endcapture%}
{%capture enhanced%}/assets/full_res/cookbook_{{page.number}}_enhanced.jpg{%endcapture%}

{%case page.number%}
    {% when "cover" %}
        {%assign next = "title" %}
    {%when  "title" %}
        {%assign next = "001" %}
        {%assign prev = "cover" %}
    {%when "001" %}
        {%assign next = "002" %}
        {%assign prev = "title" %}
    {%when "209" %}
        {%assign prev = "208" %}
    {%else %}
        {%assign numeric_page = page.number | to_integer %}
        {%assign next_num = numeric_page | plus: 1 %}
        {%assign prev_num = numeric_page | minus: 1 %}
        {%assign next = next_num | prepend: '000' | slice: -3, 3 %}
        {%assign prev = prev_num | prepend: '000' | slice: -3, 3 %}
{%endcase %}

{%if prev %}
    {%capture prev_url%}/pages/{{prev}}.html{% endcapture %}
    {%capture prev_link%}[Previous Page]({{prev_url | relative_url}}){% endcapture %}
{%endif%}
{%if next %}
    {%capture next_url%}/pages/{{next}}.html{% endcapture %}
    {%capture next_link%}[Next Page]({{next_url | relative_url}}){% endcapture %}
{%endif%}
{%if prev and next %}
    {%capture prev_next_sep %} | {% endcapture %}
{%endif%}

![Page {{page.number}}]({{web | relative_url}})
[Original Full Resolution]({{orig | relative_url}}) | [Enhanced Full Resolution]({{enhanced | relative_url}})<br/>
{{prev_link}}{{prev_next_sep}}{{next_link}}
