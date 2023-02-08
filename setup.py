# -*- coding: utf-8 -*-

from setuptools import setup
import subprocess
import os

PACKAGE = "tesouro_direto_br"

with open('README.md', encoding='utf-8') as f:
	long_description = f.read()

out = subprocess.Popen(['python', os.path.join('src', PACKAGE, 'version.py')], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
stdout, _ = out.communicate()
version = stdout.decode("utf-8").strip()
print(version)

modules = \
[PACKAGE]
install_requires = \
[
 'pandas>=1.5.3,<2.0.0',
 'requests>=2.28.2,<3.0.0',
 'matplotlib>=3.6.3,<4.0.0',
 'comparar-fundos-br>=0.0.7,<0.1.0',
 'pyettj>=0.2.4,<0.3.0'
 ]

setup_kwargs = {
    'name': PACKAGE,
    'version': version,
    'description': """ Gerenciamento da Carteira de Titulos Publicos Federais com dados do Tesouro Direto """,
	'long_description_content_type': 'text/markdown',
    'long_description': long_description,
    'author': 'Rafael Rodrigues',
    'author_email': 'rafael.rafarod@gmail.com',
    'maintainer': None,
    'maintainer_email': None,
    'url': f"https://github.com/rafa-rod/{PACKAGE}",
    'py_modules': modules,
    'include_package_data': True,
    'install_requires': install_requires,
    'python_requires': '>=3.8,<4.0',
}

setup(**setup_kwargs)