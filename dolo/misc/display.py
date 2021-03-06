 

    
def pcat(filename, target='ipython'):

    HTML_TEMPLATE = """<style>
    {}
    </style>
    {}
    """
    
    from pygments.lexers import get_lexer_for_filename
    lexer = get_lexer_for_filename(filename, stripall=True)

    from pygments.formatters import HtmlFormatter, TerminalFormatter
    from pygments import highlight
            
    with open(filename) as f:        
        code = f.read()
        
    try:
        assert(target=='ipython')
        from IPython.display import HTML, display
        from pygments.formatters import HtmlFormatter
        formatter = HtmlFormatter(linenos=True, cssclass="source")
        html_code = highlight(code, lexer, formatter)
        css = formatter.get_style_defs()
        html = HTML_TEMPLATE.format(css, html_code)
        htmlres = HTML(html)

        return htmlres
    
    except Exception as e:
        print(e)
        pass
    
    formatter = TerminalFormatter()
    output = highlight(code,lexer,formatter)
    print(output)