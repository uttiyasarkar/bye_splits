#include <iostream>
#include "include/skim.h"

#include <stdio.h>  // for printf()
#include <stdlib.h> // for strtol()
#include <errno.h>  // for errno
#include <limits.h> // for INT_MIN and INT_MAX
#include <string.h>  // for strlen

int convert_to_int(char** argv, int idx) {
  char* p;
  errno = 0; // not 'int errno', because the '#include' already defined it
  long arg = strtol(argv[idx], &p, 10);
  if (*p != '\0' || errno != 0) {
	return 1; // In main(), returning non-zero means failure
  }

  if (arg < INT_MIN || arg > INT_MAX) {
	return 1;
  }
  int arg_int = arg;

  // Everything went well, print it as a regular number plus a newline
  return arg_int;
}

//Run with ./produce.exe photons
int main(int argc, char **argv) {
  std::string dir = "/eos/user/b/bfontana/FPGAs/new_algos/";
  std::string tree_name = "FloatingpointMixedbcstcrealsig4DummyHistomaxxydr015GenmatchGenclustersntuple/HGCalTriggerNtuple";

  if (strlen(argv[1]) == 0) {
	return 1; // empty string
  }

  //process_program_options(argc, argv);
  string particle = std::string(argv[1]);

  std::string infile = particle + "_0PU_bc_stc_hadd.root";
  std::string outfile = "skim_small_" + infile;
  skim(tree_name, dir + infile, dir + outfile, particle);
  return 0;
}
