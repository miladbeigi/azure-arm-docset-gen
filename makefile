.PHONY: install run build clean help

PYTHON = python
PIP = pip
SOURCE_FILE = main.py
REQUIREMENTS = requirements.txt
DB_FILE = docSet.dsidx
DOWNLOAD_DIR = downloaded_pages
DOCSET_DIR = ./Azure.docset/Contents/Resources

install:
	$(PIP) install -r $(REQUIREMENTS)

run: install
	$(PYTHON) $(SOURCE_FILE)

build: run
	cp $(DB_FILE) $(DOCSET_DIR)/$(DB_FILE)
	cp -r $(DOWNLOAD_DIR)/*.html $(DOCSET_DIR)/Documents/
	tar --exclude='.DS_Store' -cvzf Azure.tgz Azure.docset

clean:
	rm -f $(DB_FILE)
	rm -rf $(DOWNLOAD_DIR)

help:
	@echo "install - install dependencies"
	@echo "run - run the main script"
	@echo "build - build the docset"
	@echo "clean - remove generated files"