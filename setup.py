from setuptools import setup, find_packages

setup(name='pyduin',
      version='0.2',
      description='Extensive arduino abstraction',
      url='http://github.com/SteffenKockel/pyduin',
      author='Steffen Kockel',
      author_email='info@steffen-kockel.de',
      license='GPLv3',
      packages=find_packages(),
      zip_safe=False,
      install_requires=['pyserial','PyYAML','requests','pyliblzma','termcolor'],
      python_requires='>2.6, <3',
      scripts=['pyduin/arduino_cli.py'],
      data_files=[('/usr/share/pyduin/pinfiles',['pinfiles/nano.yml']),
      			  ('/usr/share/pyduin/ino', ['ino/pyduin.ino'])
      	],
      classifiers=[
	    # How mature is this project? Common values are
	    #   3 - Alpha
	    #   4 - Beta
	    #   5 - Production/Stable
	    'Development Status :: 3 - Alpha',

	    # Indicate who your project is intended for
	    'Intended Audience :: Developers',
		'Topic :: Software Development :: Libraries :: Python Modules',
	    # Pick your license as you wish (should match "license" above)
	     'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',

	    # Specify the Python versions you support here. In particular, ensure
	    # that you indicate whether you support Python 2, Python 3 or both.
	    'Programming Language :: Python :: 2.7',
		],
	  project_urls={
	    'Documentation': 'http://github.com/SteffenKockel/pyduin',
	    # 'Funding': 'https://donate.pypi.org',
	    # 'Say Thanks!': 'http://saythanks.io/to/example',
	    'Source': 'http://github.com/SteffenKockel/pyduin',
	    'Tracker': 'http://github.com/SteffenKockel/pyduin/issues',
	    },
      )
