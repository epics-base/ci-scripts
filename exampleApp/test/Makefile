#*************************************************************************
# Copyright (c) 2020 ITER Organization.
# EPICS BASE is distributed subject to a Software License Agreement found
# in the file LICENSE that is included with this distribution.
#*************************************************************************
CURDIR := $(patsubst %/,%,$(dir $(lastword $(MAKEFILE_LIST))))
TOP = ../..

include $(TOP)/configure/CONFIG

# use the new RSET definition
USR_CPPFLAGS += -DUSE_TYPED_RSET

TARGETS += $(COMMON_DIR)/exampleTest.dbd
DBDDEPENDS_FILES += exampleTest.dbd$(DEP)
exampleTest_DBD += example.dbd

TESTFILES += $(COMMON_DIR)/exampleTest.dbd

testHarness_SRCS += exampleTest_registerRecordDeviceDriver.cpp

PROD_LIBS += exampleSupport
ifneq ($(SNCSEQ),)
    PROD_LIBS += seq pv
endif
PROD_LIBS += $(EPICS_BASE_IOC_LIBS)

TESTPROD_HOST += exampleTest
exampleTest_SRCS += exampleTest.c
exampleTest_SRCS += exampleTest_registerRecordDeviceDriver.cpp
testHarness_SRCS += exampleTest.c
TESTFILES += ../../../db/dbExample1.db
TESTS += exampleTest

# This runs all the test programs in a known working order:
testHarness_SRCS += epicsRunExampleTests.c

exampleTestHarness_SRCS += $(testHarness_SRCS)
exampleTestHarness_SRCS_RTEMS += rtemsTestHarness.c

ifdef BASE_7_0
PROD_SRCS_RTEMS += rtemsTestData.c
endif

PROD_vxWorks = exampleTestHarness
PROD_RTEMS = exampleTestHarness

TESTSPEC_vxWorks = exampleTestHarness.munch; epicsRunExampleTests
TESTSPEC_RTEMS = exampleTestHarness.boot; epicsRunExampleTests

TESTSCRIPTS_HOST += $(TESTS:%=%.t)
ifneq ($(filter $(T_A),$(CROSS_COMPILER_RUNTEST_ARCHS)),)
TESTPROD_RTEMS = $(TESTPROD_HOST)
TESTSCRIPTS_RTEMS += $(TESTS:%=%.t)
endif

include $(TOP)/configure/RULES

ifdef BASE_7_0
rtemsTestData.c : $(TESTFILES) $(TOOLS)/epicsMakeMemFs.pl
	$(PERL) $(TOOLS)/epicsMakeMemFs.pl $@ epicsRtemsFSImage $(TESTFILES)
endif
