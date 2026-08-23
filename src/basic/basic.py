'''Entry point for the BASIC interpreter REPL.'''

from basic.repl import repl

def main() -> None:
  '''Print the startup banner and run the REPL.'''
  print('BASIC')
  print('To exit, type EXIT or QUIT and press Enter.')
  repl()

if __name__ == '__main__':
  main()
