"""Copy-on-write sorted pages for exact painter orders.

An edit copies at most two small pages per changed cell, not the whole scene.
Published sequences remain immutable so cached views and snapshots stay valid.
"""
from bisect import bisect_left
from itertools import chain


def painter_key(item):
    return item[0], item[3], item[1], item[2]


class DrawOrder:
    PAGE = 256

    def __init__(self, items=()):
        self.pages = [tuple(items[i:i+self.PAGE]) for i in range(0,len(items),self.PAGE)]
        self.ends = [painter_key(page[-1]) for page in self.pages]
        self.length = len(items)

    def __len__(self):
        return self.length

    def __iter__(self):
        return chain.from_iterable(self.pages)

    def __eq__(self, other):
        return len(self)==len(other) and all(a==b for a,b in zip(self,other))

    def __getitem__(self, index):
        if isinstance(index,slice):
            start,stop,step=index.indices(len(self))
            if step!=1:return tuple(self)[index]
            result=[]; offset=0
            for page in self.pages:
                end=offset+len(page)
                if end>start and offset<stop:result.extend(page[max(0,start-offset):stop-offset])
                if end>=stop:break
                offset=end
            return tuple(result)
        if index<0:index+=len(self)
        if not 0<=index<len(self):raise IndexError(index)
        for page in self.pages:
            if index<len(page):return page[index]
            index-=len(page)

    def patched(self, removals, additions):
        result=object.__new__(type(self))
        result.pages=self.pages.copy(); result.ends=self.ends.copy(); result.length=self.length
        for key in removals:result._change(key,None)
        for item in additions:result._change(painter_key(item),item)
        return result

    def _change(self,key,item):
        page_index=bisect_left(self.ends,key)
        if page_index==len(self.pages):
            if item is None:return
            if not self.pages:
                self.pages=[(item,)];self.ends=[key];self.length=1;return
            page_index-=1
        page=list(self.pages[page_index])
        index=bisect_left(page,key,key=painter_key)
        if index<len(page) and painter_key(page[index])==key:
            page.pop(index);self.length-=1
        if item is not None:page.insert(index,item);self.length+=1
        pages=[tuple(page)] if page else []
        if len(page)>self.PAGE*2:pages=[tuple(page[:self.PAGE]),tuple(page[self.PAGE:])]
        self.pages[page_index:page_index+1]=pages
        self.ends[page_index:page_index+1]=[painter_key(p[-1]) for p in pages]
