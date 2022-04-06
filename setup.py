from setuptools import setup, find_packages

setup(
	name="fcdevuty-package",
	version="0.1.0",
	install_requires=["pyserial", "intelhex"],
	packages=find_packages(),
	entry_points={
		"console_scripts": [
			"fcdevuty=src.app:main"
		]
	}
)
