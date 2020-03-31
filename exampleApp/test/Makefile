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

DBD = exampleTest.dbd
exampleTest_DBD += example.dbd

PROD_LIBS += exampleSupport
ifneq ($(SNCSEQ),)
    PROD_LIBS += seq pv
endif
PROD_LIBS += $(EPICS_BASE_IOC_LIBS)

TESTPROD_HOST += exampleTest
exampleTest_SRCS += exampleTest.c
exampleTest_SRCS += exampleTest_registerRecordDeviceDriver.cpp
TESTS += exampleTest

TESTSCRIPTS_HOST += $(TESTS:%=%.t)

include $(TOP)/configure/RULES
