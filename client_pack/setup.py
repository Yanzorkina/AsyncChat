from setuptools import setup, find_packages

setup(name="mess_client_gb_2404",
      version="0.0.1",
      description="mess_client_gb_2404",
      author="Alina Yanzorkina",
      author_email="doc.alina@bk.ru",
      packages=find_packages(),
      install_requires=['PyQt5', 'sqlalchemy', 'pycryptodome', 'pycryptodomex']
      )