/*************************************************************************\
* Copyright (c) 2011 UChicago Argonne LLC, as Operator of Argonne
*     National Laboratory.
* EPICS BASE is distributed subject to a Software License Agreement found
* in file LICENSE that is included with this distribution.
\*************************************************************************/

/*
 * Run Example tests as a batch.
 *
 */

#include "epicsUnitTest.h"
#include "epicsExit.h"
#include "dbmf.h"

int exampleTest(void);

void epicsRunExampleTests(void)
{
    testHarness();

    runTest(exampleTest);

    dbmfFreeChunks();

    epicsExit(0);   /* Trigger test harness */
}
