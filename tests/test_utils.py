from supplement.utils import WeakedList

def test_weaked_list():
    class A(object): pass

    wl = WeakedList()

    holder1 = [A(), A()]
    holder2 = [A()]
    holder3 = {'key':A()}

    wl.append(holder1[0])
    wl.append(holder1[1])
    wl.append(holder2[0])
    wl.append(holder3['key'])

    assert [holder1[0], holder1[1], holder2[0], holder3['key']] == list(wl)

    holder1[:] = []
    assert [holder2[0], holder3['key']] == list(wl)

    del holder3['key']
    assert [holder2[0]] == list(wl)
