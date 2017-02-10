from bs4 import BeautifulSoup

acceptable_elements = ['a', 'abbr', 'acronym', 'address', 'area', 'b', 'big',
      'blockquote', 'br', 'button', 'caption', 'center', 'cite', 'code', 'col',
      'colgroup', 'dd', 'del', 'dfn', 'dir', 'div', 'dl', 'dt', 'em',
      'font', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'img',
      'ins', 'kbd', 'label', 'legend', 'li', 'map', 'menu', 'ol',
      'p', 'pre', 'q', 's', 'samp', 'small', 'span', 'strike',
      'strong', 'sub', 'sup', 'table', 'tbody', 'td', 'tfoot', 'th',
      'thead', 'tr', 'tt', 'u', 'ul', 'var', 'html', 'body', 'iframe']

acceptable_attributes = ['abbr', 'accept', 'accept-charset', 'accesskey',
  'action', 'align', 'alt', 'axis', 'border', 'cellpadding', 'cellspacing',
  'char', 'charoff', 'charset', 'checked', 'cite', 'clear', 'cols', 'class',
  'colspan', 'color', 'compact', 'coords', 'datetime', 'dir',
  'enctype', 'for', 'headers', 'height', 'href', 'hreflang', 'hspace',
  'id', 'ismap', 'label', 'lang', 'longdesc', 'maxlength', 'method',
  'multiple', 'name', 'nohref', 'noshade', 'nowrap', 'prompt',
  'rel', 'rev', 'rows', 'rowspan', 'rules', 'scope', 'shape', 'size',
  'span', 'src', 'start', 'summary', 'tabindex', 'target', 'title', 'type',
  'usemap', 'valign', 'value', 'vspace', 'width', 'style',
  'allowFullscreen']

def lose_html_and_body_tags(soup):
    tag_str_list = []
    if(soup.html.body):
        tag_str_list = [
            str(tag)
            for tag in
            soup.html.body.findChildren(recursive=False)
        ]
    return ''.join(tag_str_list) if tag_str_list else ''

def clean_html( fragment ):
    while True:
        soup = BeautifulSoup( fragment , "lxml")
        removed = False
        for tag in soup.findAll(True): # find all tags
            if tag.name not in acceptable_elements:
                tag.extract() # remove the bad ones
                removed = True
            else: # it might have bad attributes
                # a better way to get all attributes?
                tag_attributes = dict(tag.attrs)
                for attr in tag_attributes:
                    if attr not in acceptable_attributes:
                        del tag[attr]

        # turn it back to html
        fragment = soup
        print(soup)

        return lose_html_and_body_tags(soup)
