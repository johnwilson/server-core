from pyparsing import Suppress, Word, Literal, quotedString, nums, removeQuotes
from pyparsing import Combine, delimitedList, Group, Optional, OneOrMore, ZeroOrMore
from pyparsing import StringEnd, CaselessKeyword, oneOf, alphas, alphanums, srange, restOfLine, SkipTo
from pyparsing import ParseException, Regex

import json
import logging
from common import Service
import common
import re

class ParserService(Service):
    
    def __init__(self, id, name="parser", configfile=None):
        Service.__init__(self, id, name, configfile)
        self.parser_cmdline = CommandLineParser()
        self.parser_jsoncmdline = JSONCommandLineParser()
        self.parser_bql = BQLParser()
    
    def processRequest(self, command, command_data):        
        try:
            if command == "parser.commandline":
                _parsed =self.parser_cmdline.parseString(command_data)
                data = {"command":list(_parsed["command"])}
                return common.SuccessResponse(data)
            elif command == "parser.jsoncommandline":
                _parsed =self.parser_jsoncmdline.parseString(command_data)
                data = {"command":list(_parsed["command"]),
                        "filedata":_parsed["filedata"]}
                return common.SuccessResponse(data)
            elif command == "parser.bql":
                _parsed = self.parser_bql.parseString(command_data)
                return common.SuccessResponse(_parsed)
            else:
                return common.InvalidRequestError("parser '%s' doesn't exist" % command)
        except ParseException, err:
            return common.INT_ServiceError(str(err))

class BQLParser(object):
    def __init__(self):
        self.queryparts = {}
        
        stringValue = quotedString.setParseAction(removeQuotes)
        intValue = Word(nums).setParseAction(lambda t:int(t[0]))
        floatValue = Combine(Word(nums) + "." + Word(nums)).setParseAction(lambda t:float(t[0]))
        value = stringValue | floatValue | intValue
        valueList = delimitedList(value)
        openparenthesis = Suppress(Literal("("))
        closeparenthesis = Suppress(Literal(")"))
        opensquarebracket = Suppress(Literal("["))
        closesquarebracket = Suppress(Literal("]"))
        comma = Suppress(Literal(","))
        field = quotedString.setParseAction(removeQuotes)
        fieldList = delimitedList(field)
        
        BQLType = CaselessKeyword("$double") | CaselessKeyword("$string") | \
                  CaselessKeyword("$object") | CaselessKeyword("$array") | \
                  CaselessKeyword("$binary") | CaselessKeyword("$bool") | \
                  CaselessKeyword("$date") | CaselessKeyword("$null") | \
                  CaselessKeyword("$int32") | CaselessKeyword("$int") | \
                  CaselessKeyword("$int64") | CaselessKeyword("$timestamp") | \
                  CaselessKeyword("$exists") | CaselessKeyword("$nexists")
        
        BQLCompareOperator = CaselessKeyword("$lt") | CaselessKeyword("$lte") | \
                             CaselessKeyword("$gt") | CaselessKeyword("$gte") | \
                             CaselessKeyword("$eq") | CaselessKeyword("$neq") | \
                             CaselessKeyword("$regex")
                             
        
        BQLIncludeOperator = CaselessKeyword("$in") | CaselessKeyword("$nin")
        
        
        typecheck = BQLType + openparenthesis + Optional(fieldList) + closeparenthesis
        typecheck.setParseAction(self.parseType)
        
        comparison = BQLCompareOperator + openparenthesis + field + comma + value + closeparenthesis
        comparison.setParseAction(self.parseComparison)
        
        inclusion = BQLIncludeOperator + openparenthesis + field + comma + \
                    opensquarebracket + Optional(valueList) + closesquarebracket + closeparenthesis
        inclusion.setParseAction(self.parseInclusion)
        
        BQLTokens = ZeroOrMore(typecheck | comparison | inclusion)
        
        #-----------------------------------------------------------------------
        # Query Select Statement Parsing
        #-----------------------------------------------------------------------
        
        SELECT = (Suppress(CaselessKeyword("Select")) + openparenthesis + \
                 Optional(fieldList) + closeparenthesis)
        SELECT.setParseAction(self.parseSelect)
        
        #-----------------------------------------------------------------------
        # Query From Statement Parsing
        #-----------------------------------------------------------------------
        
        FROM = (Suppress(CaselessKeyword("From")) + openparenthesis + \
               Optional(fieldList) + closeparenthesis)
        FROM.setParseAction(self.parseFrom)
        
        #-----------------------------------------------------------------------
        # Query Where Statement Parsing
        #-----------------------------------------------------------------------
        
        AND = (Suppress(CaselessKeyword("And")) + openparenthesis + \
                    BQLTokens + closeparenthesis).setParseAction(self.parseAnd)
        
        OR = (Suppress(CaselessKeyword("Or")) + openparenthesis + \
                   BQLTokens + closeparenthesis).setParseAction(self.parseOr)
        
        WHERE = (Suppress(CaselessKeyword("Where")) + BQLTokens).setParseAction(self.parseWhere)\
                + ZeroOrMore(OR | AND)
        
        #-----------------------------------------------------------------------
        # Resultset Management Statement Parsing
        #-----------------------------------------------------------------------
        
        # distinct
        DISTINCT = (Suppress(CaselessKeyword("Distinct")) + openparenthesis + \
                   fieldList + closeparenthesis).setParseAction(self.parseDistinct)
        
        # limit
        LIMIT = (Suppress(CaselessKeyword("Limit")) + openparenthesis + \
                      intValue + closeparenthesis).setParseAction(self.parseLimit)
        
        # sort ascending
        SORT = (CaselessKeyword("Asc") | CaselessKeyword("Desc")) + openparenthesis + \
                  fieldList + closeparenthesis
        SORT.setParseAction(self.parseSort)
        
        CURSOR_CONTROL = ZeroOrMore(DISTINCT | LIMIT | SORT)
        
        #-----------------------------------------------------------------------
        # Query parser build up
        #-----------------------------------------------------------------------
        self.parser = SELECT + FROM + Optional(WHERE) + CURSOR_CONTROL + StringEnd()
        
    def parseType(self, s, loc, toks):
        values = []
        _type = toks[0]
        if _type == "$double":
            for field in toks[1:]:
                value = {field:{"$type":1}}
                values.append(value)
        elif _type == "$string":
            for field in toks[1:]:
                value = {field:{"$type":2}}
                values.append(value)
        elif _type == "$object":
            for field in toks[1:]:
                value = {field:{"$type":3}}
                values.append(value)
        elif _type == "$array":
            for field in toks[1:]:
                value = {field:{"$type":4}}
                values.append(value)
        elif _type == "$binary":
            for field in toks[1:]:
                value = {field:{"$type":5}}
                values.append(value)
        elif _type == "$bool":
            for field in toks[1:]:
                value = {field:{"$type":8}}
                values.append(value)
        elif _type == "$date":
            for field in toks[1:]:
                value = {field:{"$type":9}}
                values.append(value)
        elif _type == "$null":
            for field in toks[1:]:
                value = {field:{"$type":10}}
                values.append(value)
        elif _type == "$int32":
            for field in toks[1:]:
                value = {field:{"$type":16}}
                values.append(value)
        elif _type == "$int":
            for field in toks[1:]:
                value = {field:{"$type":16}}
                values.append(value)
        elif _type == "$int64":
            for field in toks[1:]:
                value = {field:{"$type":18}}
                values.append(value)
        elif _type == "$timestamp":
            for field in toks[1:]:
                value = {field:{"$type":17}}
                values.append(value)
        elif _type == "$exists":
            for field in toks[1:]:
                value = {field:{"$exists":True}}
                values.append(value)
        elif _type == "$nexists":
            for field in toks[1:]:
                value = {field:{"$exists":False}}
                values.append(value)
        
        return values
    
    def parseComparison(self, s, loc, toks):
        value = {}
        _type = toks[0]
        if _type == "$lt":
            value = {toks[1]:{"$lt":toks[2]}}
        elif _type == "$lte":
            value = {toks[1]:{"$lte":toks[2]}}
        elif _type == "$gt":
            value = {toks[1]:{"$gt":toks[2]}}
        elif _type == "$gte":
            value = {toks[1]:{"$gte":toks[2]}}
        elif _type == "$eq":
            value = {toks[1]:toks[2]}
        elif _type == "$neq":
            value = {toks[1]:{"$ne":toks[2]}}
        elif _type == "$regex":
            value = {toks[1]:{"$regex":toks[2]}}
        return value
    
    def parseInclusion(self, s, loc, toks):
        value = {}
        _type = toks[0]
        if _type == "$in":
            value = {toks[1]:{"$in":toks[2:]}}
        elif _type == "$nin":
            value = {toks[1]:{"$nin":toks[2:]}}
        return value
    
    def parseSort(self, s, loc, toks):        
        _type = toks[0]        
        if _type == "Asc":
            for item in toks[1:]:
                self.queryparts["sort"].append((item,1))
        else:
            for item in toks[1:]:
                self.queryparts["sort"].append((item,-1))
                
    def parseDistinct(self, s, loc, toks):
        for item in toks:
            self.queryparts["distinct"].append(item)
    
    def parseLimit(self, s, loc, toks):
        self.queryparts["limit"] = toks[0]
    
    def parseSelect(self, s, loc, toks):
        for item in toks:
            self.queryparts["select"].append(item)
            
    def parseFrom(self, s, loc, toks):
        for item in toks:
            self.queryparts["from"].append(item)
            
    def parseAnd(self, s, loc, toks):
        for item in toks:
            self.queryparts["and"].append(item)
        
    def parseOr(self, s, loc, toks):
        for item in toks:
            self.queryparts["or"].append(item)
            
    def parseWhere(self, s, loc, toks):
        for item in toks:
            self.queryparts["where"].update(item)
    
    def parseString(self, querystring):
        self.queryparts = {"where":{},
                           "sort":[],
                           "distinct":[],
                           "select":[],
                           "from":[],
                           "and":[],
                           "or":[]}
        self.parser.parseString(querystring)
        return self.queryparts

class JSONCommandLineParser(object):
    def __init__(self):
        dash = Word("-",max=2)
        operator = oneOf(": =")
        
        argValueType1 = quotedString.setParseAction(removeQuotes)
        argValueType2 = Regex("[a-zA-Z0-9_\./]+")
        
        positionalArgument = (argValueType1 | argValueType2)
        regularArgument = Combine(dash + Word(alphas) + operator + (argValueType1 | argValueType2))
        novalueArgument = Combine(dash + Word(alphas))
        
        arguments = ZeroOrMore(positionalArgument | regularArgument | novalueArgument)
        
        self.parser = Group(Word(alphas) + arguments).setResultsName("command") + SkipTo(Word("{[")).setParseAction(self.jsonData)
        
    def jsonData(self, commandtext, location, tokens):
        startindex = location + len("".join(tokens))
        return commandtext[startindex:]
    
    def parseString(self, querystring):
        result = self.parser.parseString(querystring)
        return {"command":result.command,
                "filedata":result[1]}
    
class CommandLineParser(object):
    def __init__(self):
        dash = Word("-",max=2)
        operator = oneOf(": =")
        
        argValueType1 = quotedString.setParseAction(removeQuotes)
        argValueType2 = Regex("[a-zA-Z0-9_\./]+")
        
        positionalArgument = (argValueType1 | argValueType2)
        regularArgument = Combine(dash + Word(alphas) + operator + (argValueType1 | argValueType2))
        novalueArgument = Combine(dash + Word(alphas))
        
        arguments = ZeroOrMore(positionalArgument | regularArgument | novalueArgument)
        
        self.parser = Group(Word(alphas) + arguments).setResultsName("command")
        
    def parseString(self, querystring):
        return self.parser.parseString(querystring)
        
if __name__ == '__main__':    
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("-i","--id",action="store",type=int,default=1)
    parsed = parser.parse_args()
    
    s = ParserService(id=parsed.id)
    try:
        s.run()
    except KeyboardInterrupt:
        print "\nexiting"
