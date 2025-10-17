from html.parser import HTMLParser

class NewsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.articles = []
        self.current_article = {}
        self.in_article = False
        self.in_title = False
        self.current_title = ""
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        if tag == 'div' and 'article' in attrs_dict.get('class', ''):
            self.in_article = True
            self.current_article = {}
            self.current_title = ""
        
        elif tag in ['h1', 'h2', 'h3', 'h4'] and self.in_article:
            self.in_title = True

    def handle_endtag(self, tag):
        if tag in ['h1', 'h2', 'h3', 'h4'] and self.in_title:
            self.in_title = False
            if self.current_title:
                self.current_article['title'] = self.current_title.strip()
                self.current_article['link'] = "https://itproger.com/news"
                self.articles.append(self.current_article.copy())
                
        elif tag == 'div' and self.in_article:
            self.in_article = False

    def handle_data(self, data):
        if self.in_title:
            self.current_title += data

def parse_news(html):
    parser = NewsParser()
    parser.feed(html)
    return parser.articles
