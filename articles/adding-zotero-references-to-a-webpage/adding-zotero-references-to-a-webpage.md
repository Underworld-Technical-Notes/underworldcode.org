---
title: An automated (zotero) bibliography in a webpage
date: 2019-10-23
authors:
  - name: Louis Moresi
    orcid: 0000-0003-3685-174X
    affiliations:
      - Australian National University
doi: 10.59350/qnz5b-4dt16
license: CC-BY-4.0
banner: figures/banner.png
keywords:
  - Tricks of the Trade
exports:
  - format: typst
    source_url: https://www.underworldcode.org/adding-zotero-references-to-a-webpage/
    template: ../../templates/pdf
    output: adding-zotero-references-to-a-webpage.pdf
    article_id: UWTN 2019-003
    article_version: 1.0.0
parts:
  abstract: "How we added an auto-updating set of citations to underworld in our publications [https://www.underworldcode.org/publications-using-uw/] webpage. We need to curate all the publications that we can find that use the underworld [https://www.underworldcode.org/intro-to-underworld/] geodynamics code and provide this information on our website. To avoid needless repetition, we take advantage of the fact that nearly all the information we require is online and automatically construct the bibliograph"
---
<div class="uwtn-banner"><img src="figures/banner.png" alt=""></div>

*How we added an auto-updating set of citations to underworld in our [publications](/publications-using-uw/) webpage. *

We need to curate all the publications that we can find that use the [underworld](/intro-to-underworld/) geodynamics code and provide this information on our website. To avoid needless repetition, we take advantage of the fact that nearly all the information we require is online and automatically construct the bibliography from an [online public zotero library](https://www.zotero.org/groups/2386948/underworld-geodynamics-community/items/collectionKey/QNARWBUC).

## Javascript Code

The code to collect one year's worth of data using the zotero api and render it online is very simple:

```html
<h2> 2019 </h2>
<div id="pubs-2019"> Loading ... </div>

<script>
groupID = '2386948'
collectionKey = 'QNARWBUC'

fetch(`https://api.zotero.org/groups/${groupID}/collections/${collectionKey}/items?format=bib&style=apa&linkwrap=1&q=2019`)
				.then(function (response) {
					return response.text();
				})
				.then(function(body) {
					document.getElementById("pubs-2019").innerHTML = body;
				}); 
    document.write("<br/>")
</script>
```

This works by sending a structured query to zotero asking for information for a specific library (here the  library for the underworld-community group which has an ID of *2386948* and a specific collection of data with the Key of *QNARWBUC*). The result of the query is then loaded into the content of the `<div id="pubs-2019">` tag when the query has completed.

It produces the following output

###  2019

Loading ...

We build this into a loop for all the years we want to query like this:

```html
<script>
for (let i = 2019; i >= 2005; i--) {
   document.write(`<h2 > ${i} </h2>` );
   document.write(`<div id=year${i}>` + `Loading ${i} publications </div>` );

    fetch(`https://api.zotero.org/groups/2386948/collections/QNARWBUC/items?format=bib&style=apa&linkwrap=1&q=${i}`)
				.then(function (response) {
					return response.text();
				})
				.then(function(body) {
					document.getElementById("year"+i).innerHTML = body;
				}); 
    document.write("<br/>")
}
</script>
```

The notable change is that we add the using a `document.write()` call so that we can generate unique tags. The `fetch` command is acting asynchronously so we do need to be careful to name each tag uniquely as we don't know the order in which the subsitutions will be made.

## How can I use this ?

To find the groupID and collectionKey for a particular group library, look at the URL itself. For the library above, the format is https://www.zotero.org/groups/`2386948`/underworld-geodynamics-community/items/collectionKey/`QNARWBUC`.

For an individual, you can access the "my publications" public library with the following script (again, looking at the zotero URL to work out who you are — unless you are me in which case this is already just fine).

```html
<script>
for (let i = 2019; i >= 1995; i--) {
   document.write(`<h2 > ${i} </h2>` );
   document.write(`<div id=year${i}>` + `Loading ${i} publications </div>` );

    fetch(`https://api.zotero.org/users/6049345/publications/items?format=bib&style=apa&linkwrap=1&q=${i}`)
				.then(function (response) {
					return response.text();
				})
				.then(function(body) {
					document.getElementById("year"+i).innerHTML = body;
				});
    document.write("<br/>")
}
</script>
```

For more information on how to use the zotero api consult[their documentation](https://www.zotero.org/support/dev/web_api/v3/start) and particularly, see the "[basics](https://www.zotero.org/support/dev/web_api/v3/basics)" page to see how to write different queries.

## Limitations

This is not an automatically generated list of publications from the whole web that use the underworld code because we ultimately have to curate our references quite carefully.

The same applies if you want a  list of your own publications to be generated automatically — you could just link to google scholar or orcid. However, at the moment, it is hard to access those databases publicly on demand via a webpage, and their automatic discovery of publications can be somewhat hit and miss. You probably have a curating job ahead of you anyway. Hence this semi-automatic but open source / free solution.

<div class="uwtn-discuss"><div class="uwtn-discuss-head">Comments</div><div class="uwtn-discuss-body">Discussion of these notes happens in GitHub Discussions, so it stays with the source and is searchable alongside it.</div><div class="uwtn-discuss-links"><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions?discussions_q=adding-zotero-references-to-a-webpage">Read the discussion</a><a href="https://github.com/Underworld-Technical-Notes/underworldcode.org/discussions/new?category=general&title=adding-zotero-references-to-a-webpage">Start one</a></div></div>
