"""Type stubs for trafilatura under Pyright strict mode."""

def extract(
    filecontent: str | bytes,
    *,
    url: str | None = ...,
    include_comments: bool = ...,
    include_tables: bool = ...,
    include_links: bool = ...,
    include_images: bool = ...,
    favor_precision: bool = ...,
    favor_recall: bool = ...,
) -> str | None: ...
