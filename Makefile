init:
	pip install -r requirements.txt

test:
	pytest --pdb -s tests
	#pytest --pdbcls pudb.debugger:Debugger --pdb --capture=no -s tests
