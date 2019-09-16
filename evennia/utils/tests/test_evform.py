"""
Unit tests for the EvForm text form generator

"""
from django.test import TestCase
from evennia.utils import evform


class TestEvForm(TestCase):
    def test_form(self):
        self.maxDiff = None
        form1 = evform._test()
        form2 = evform._test()
        self.assertEqual(form1, form2)

        # self.assertEqual(form1, "")
        # '.------------------------------------------------.\n'
        # '|                                                |\n'
        # '|  Name: \x1b[0m\x1b[1m\x1b[32mTom\x1b[1m\x1b[32m \x1b'
        # '[1m\x1b[32mthe\x1b[1m\x1b[32m \x1b[0m   \x1b[0m    '
        # 'Account: \x1b[0m\x1b[1m\x1b[33mGriatch        '
        # '\x1b[0m\x1b[0m\x1b[1m\x1b[32m\x1b[1m\x1b[32m\x1b[1m\x1b[32m\x1b[1m\x1b[32m\x1b[0m\x1b[0m '
        # '|\n'
        # '|        \x1b[0m\x1b[1m\x1b[32mBouncer\x1b[0m    \x1b[0m                             |\n'
        # '|                                                |\n'
        # ' >----------------------------------------------< \n'
        # '|                                                |\n'
        # '| Desc:  \x1b[0mA sturdy \x1b[0m  \x1b[0m'
        # '    STR: \x1b[0m12 \x1b[0m\x1b[0m\x1b[0m\x1b[0m'
        # '    DEX: \x1b[0m10 \x1b[0m\x1b[0m\x1b[0m\x1b[0m     |\n'
        # '|        \x1b[0mfellow\x1b[0m     \x1b[0m'
        # '    INT: \x1b[0m5  \x1b[0m\x1b[0m\x1b[0m\x1b[0m'
        # '    STA: \x1b[0m18 \x1b[0m\x1b[0m\x1b[0m\x1b[0m     |\n'
        # '|        \x1b[0m           \x1b[0m'
        # '    LUC: \x1b[0m10 \x1b[0m\x1b[0m\x1b[0m'
        # '    MAG: \x1b[0m3  \x1b[0m\x1b[0m\x1b[0m     |\n'
        # '|                                                |\n'
        # ' >----------.-----------------------------------< \n'
        # '|           |                                    |\n'
        # '| \x1b[0mHP\x1b[0m|\x1b[0mMV \x1b[0m|\x1b[0mMP\x1b[0m '
        # '| \x1b[0mSkill      \x1b[0m|\x1b[0mValue     \x1b[0m'
        # '|\x1b[0mExp        \x1b[0m\x1b[0m\x1b[0m\x1b[0m\x1b[0m\x1b[0m\x1b[0m |\n'
        # '| ~~+~~~+~~ | ~~~~~~~~~~~+~~~~~~~~~~+~~~~~~~~~~~ |\n'
        # '| \x1b[0m**\x1b[0m|\x1b[0m***\x1b[0m\x1b[0m|\x1b[0m**\x1b[0m\x1b[0m '
        # '| \x1b[0mShooting   \x1b[0m|\x1b[0m12        \x1b[0m'
        # '|\x1b[0m550/1200   \x1b[0m\x1b[0m\x1b[0m\x1b[0m\x1b[0m\x1b[0m\x1b[0m\x1b[0m\x1b[0m |\n'
        # '| \x1b[0m  \x1b[0m|\x1b[0m**\x1b[0m \x1b[0m|\x1b[0m*\x1b[0m \x1b[0m '
        # '| \x1b[0mHerbalism  \x1b[0m|\x1b[0m14        \x1b[0m'
        # '|\x1b[0m990/1400   \x1b[0m\x1b[0m\x1b[0m\x1b[0m\x1b[0m\x1b[0m\x1b[0m\x1b[0m\x1b[0m |\n'
        # '| \x1b[0m  \x1b[0m|\x1b[0m   \x1b[0m|\x1b[0m  \x1b[0m '
        # '| \x1b[0mSmithing   \x1b[0m|\x1b[0m9         \x1b[0m'
        # '|\x1b[0m205/900    \x1b[0m\x1b[0m\x1b[0m\x1b[0m\x1b[0m\x1b[0m\x1b[0m |\n'
        # '|           |                                    |\n'
        # ' -----------`-------------------------------------\n'
        # ' Footer: \x1b[0mrev 1  \x1b[0m                                  \n'
        # ' info                                             \n'
        # '                                                  ')

    def test_ansi_escape(self):
        # note that in a msg() call, the result would be the  correct |-----,
        # in a print, ansi only gets called once, so ||----- is the result
        self.assertEqual(str(evform.EvForm(form={"FORM": "\n||-----"})), "||-----")
