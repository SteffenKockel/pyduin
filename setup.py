""" setyp.py """
from setuptools import setup, find_packages

setup(name='pyduin',
      version='0.6.1',
      description='Extensive Arduino abstraction',
      url='http://github.com/SteffenKockel/pyduin',
      author='Steffen Kockel',
      author_email='info@steffen-kockel.de',
      license='GPLv3',
      packages=find_packages(),
      package_dir={'pyduin': '.'},
      package_data={ 'pyduin': ["pinfiles/*.yml"]},
      zip_safe=False,
      tests_require=['coverage', 'unittest2', 'mock', 'pylint', 'flake8'],
      install_requires=['pyserial', 'PyYAML', 'requests', 'termcolor', 'platformio', 'serial'],
      python_requires='>3',
      entry_points={
      	'console_scripts':
      		['arduino=pyduin.arduino_cli:main']
      	},
      include_package_data=True,
      data_files=[('.ino', ['ino/pyduin.ino'])],
      classifiers=[
	    # How mature is this project? Common values are
	    #   3 - Alpha
	    #   4 - Beta
	    #   5 - Production/Stable
	    'Development Status :: 4 - Beta',

	    # Indicate who your project is intended for
	    'Intended Audience :: Developers',
		'Topic :: Software Development :: Libraries :: Python Modules',
	    # Pick your license as you wish (should match "license" above)
	     'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',

	    # Specify the Python versions you support here. In particular, ensure
	    # that you indicate whether you support Python 2, Python 3 or both.
	    'Programming Language :: Python :: 3',
		],
	  project_urls={
	    'Documentation': 'http://github.com/SteffenKockel/pyduin',
	    # 'Funding': 'https://donate.pypi.org',
	    # 'Say Thanks!': 'http://saythanks.io/to/example',
	    'Source': 'http://github.com/SteffenKockel/pyduin',
	    'Tracker': 'http://github.com/SteffenKockel/pyduin/issues',
	    },
      )
