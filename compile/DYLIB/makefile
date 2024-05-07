# # makefile for MoorDyn compiled as Lines.dll


# # tell to search for dependencies in parent dir
# VPATH = ../../source


# #LFLAGS = -shared -static -static-libgcc -static-libstdc++ -DMoorDyn_EXPORTS
# # LFLAGS = -shared -DMoorDyn_EXPORTS

# # CFLAGS = -c -Ofast -g -w -Wall -static -static-libgcc -static-libstdc++ -std=gnu++0x -DMoorDyn_EXPORTS -DOSX

# # Flags for compiling with clang (OSX default)
# LFLAGS = -shared -DOSX -DMoorDyn_EXPORTS -fPIC
# CFLAGS = -c -O3 -static -g -Wall -Wextra -DOSX -DMoorDyn_EXPORTS -fPIC

# CC = clang++

# all: Lines.dylib
 
# Lines.dylib: MoorDyn.o Line.o Connection.o Misc.o kiss_fft.o
# 	$(CC) $(LFLAGS) -o $@ MoorDyn.o Line.o Connection.o Misc.o kiss_fft.o
# # added linking to openGL above

# MoorDyn.o: MoorDyn.cpp MoorDyn.h Line.h Line.cpp Connection.h Connection.cpp QSlines.h Misc.h Misc.cpp
# 	$(CC) $(CFLAGS) ../../source/MoorDyn.cpp
	
# kiss_fft.o: kiss_fft.h kiss_fft.c
# 	$(CC) $(CFLAGS) ../../source/kiss_fft.c
	
# Line.o: Line.h Line.cpp Connection.h Connection.cpp QSlines.h Misc.h
# 	$(CC) $(CFLAGS) ../../source/Line.cpp

# Connection.o: Line.h Line.cpp Connection.h Connection.cpp QSlines.h Misc.h Misc.cpp
# 	$(CC) $(CFLAGS) ../../source/Connection.cpp
	
# Misc.o: Misc.h Misc.cpp
# 	$(CC) $(CFLAGS) ../../source/Misc.cpp

# clean:
# 	rm  *.o *.dylib

# -----------------------------

# makefile for MoorDyn compiled as libmoordyn2.dylib (so it can be linked with
# -lmoordyn2)
#
# Several options can be set:
#
#  - USEGL: Enables the OpenGL visualization
#  - COPTS: Compilation options. For good performance and compatibility use:
#           COPTS='-msse2 -ffast-math -DMOORDYN_SINGLEPRECISSION'
#           However, for local-only installations a more aggresive instructions
#           set can be used:
#           COPTS='-march=native -ffast-math -DMOORDYN_SINGLEPRECISSION'
#
# The following targets are provided:
#
# all: Builds the library libmoordyn.dylib
#
# test: Build libmoordyn.dylib, if not yet built, and then the tests:
#        - test_minimal
#        - test_quasi_static_chain
#
# debug: Build both targets, "all" and "test", with debug information


# # Flags for compiling with gcc (not OSX default)
# LFLAGS = -shared -static-libgcc -static-libstdc++ -DOSX -DMoorDyn_EXPORTS -fPIC
# CFLAGS = -c -O3 -g -Wall -Wextra -DOSX -DMoorDyn_EXPORTS -fPIC

# Flags for compiling with clang (OSX default)
LFLAGS = -shared -DOSX -DMoorDyn_EXPORTS -fPIC
CFLAGS = -c -O3 -static -g -Wall -Wextra -DOSX -DMoorDyn_EXPORTS -fPIC -I../../source/

ifdef USEGL
CFLAGS += -DUSEGL
LFLAGS += -lopengl32 -lglu32
endif

CFLAGS += $(COPTS)
LFLAGS += $(LOPTS)

CPPFLAGS = $(CFLAGS) -std=c++17
EXEFLAGS = -O3 -g -Wall -Wextra -DOSX $(EXEOPTS)

CC = clang++
CXX = clang++

HEADERS = $(wildcard ../../source/*.hpp)
CHEADERS = $(wildcard ../../source/*kiss*.h)
SOURCES = $(wildcard ../../source/*.cpp)
CSOURCES = $(wildcard ../../source/*kiss*.c)
OBJECTS = $(patsubst ../../source/%,%,$(patsubst %.cpp,%.o,$(SOURCES))) kiss_fft.o kiss_fftr.o

DIRGUARD = @mkdir -p $(@D)

all: libmoordyn2.dylib

libmoordyn2.dylib: $(OBJECTS) $(COBJECTS)
	$(CXX) $(LFLAGS) -o libmoordyn2.dylib $(OBJECTS) $(COBJECTS)

%.o: ../../source/%.cpp $(HEADERS)
	${CXX} $(CPPFLAGS) -o $@ $<

# %.o: ../../source/%*kiss*.c $(CHEADERS)
	# ${CXX} $(CFLAGS) -o $@ $<

kiss_fft.o: ../../source/kiss_fft.c $(CHEADERS)
	$(CC) $(CFLAGS) ../../source/kiss_fft.c

kiss_fftr.o: ../../source/kiss_fftr.c $(CHEADERS)
	$(CC) $(CFLAGS) ../../source/kiss_fftr.c

clean:
	rm -f *.o ./*/*.o *.dylib *.dylib.*
