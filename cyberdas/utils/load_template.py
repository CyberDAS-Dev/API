from os import path

import jinja2


def load_template(name: str) -> jinja2.Template:
    '''
    Возвращает загруженный шаблон jinja2.
    Аргументы:
        name(str, необходимо): имя файла с шаблоном, лежащего в
            папке cyberdas/templates
    '''

    template_path = path.join('cyberdas/templates', name + '.jinja2')
    with open(path.abspath(template_path), 'r') as f:
        content = f.read()
    return jinja2.Template(content)
