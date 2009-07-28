import unittest

class StateMachineTests(unittest.TestCase):

    def _getTargetClass(self):
        from repoze.bfg.workflow.statemachine import StateMachine
        return StateMachine

    def _makeOne(self, attr='state', transitions=None, initial_state=None):
        klass = self._getTargetClass()
        return klass(attr, transitions, initial_state)

    def test_add_state_info_state_exists(self):
        sm = self._makeOne()
        sm._states = {'foo':{'c':5}}
        sm.add_state_info('foo', a=1, b=2)
        self.assertEqual(sm._states, {'foo':{'a':1, 'b':2, 'c':5}})

    def test_add_state_info_state_doesntexist(self):
        sm = self._makeOne()
        sm.add_state_info('foo', a=1, b=2)
        self.assertEqual(sm._states, {'foo':{'a':1, 'b':2}})

    def test_add_transition(self):
        sm = self._makeOne()
        sm.add_transition('make_public', 'private', 'public', None, a=1)
        sm.add_transition('make_private', 'public', 'private', None, b=2)
        self.assertEqual(len(sm._transitions), 2)
        transitions = sm._transitions
        self.assertEqual(transitions[0]['id'], 'make_public')
        self.assertEqual(transitions[0]['from_state'], 'private')
        self.assertEqual(transitions[0]['to_state'], 'public')
        self.assertEqual(transitions[0]['callback'], None)
        self.assertEqual(transitions[0]['a'], 1)
        self.assertEqual(transitions[1]['id'], 'make_private')
        self.assertEqual(transitions[1]['from_state'], 'public')
        self.assertEqual(transitions[1]['to_state'], 'private')
        self.assertEqual(transitions[1]['callback'], None)
        self.assertEqual(transitions[1]['b'], 2)

        self.assertEqual(len(sm._states), 2)

    def _add_transitions(self, sm, callback=None):
        sm._transitions.extend(
            [
            dict(id='publish', from_state='pending', to_state='published',
                 callback=callback),
            dict(id='reject', from_state='pending', to_state='private',
                 callback=callback),
            dict(id='retract', from_state='published', to_state='pending',
                 callback=callback),
            dict(id='submit', from_state='private', to_state='pending',
                 callback=callback),
            ]
            )

    def test_transitions_default_from_state(self):
        sm = self._makeOne(initial_state='pending')
        self._add_transitions(sm)
        ob = ReviewedObject()
        result = sm.transitions(ob)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], 'publish')
        self.assertEqual(result[1]['id'], 'reject')

    def test_transitions_overridden_from_state(self):
        sm = self._makeOne(initial_state='pending')
        self._add_transitions(sm)
        ob = ReviewedObject()
        result = sm.transitions(ob, from_state='private')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], 'submit')

    def test_transitions_context_has_state(self):
        sm = self._makeOne(initial_state='pending')
        self._add_transitions(sm)
        ob = ReviewedObject()
        ob.state = 'published'
        result = sm.transitions(ob)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['id'], 'retract')

    def test_execute(self):
        sm = self._makeOne(initial_state='pending')
        args = []
        def dummy(context, transition):
            args.append((context, transition))
        self._add_transitions(sm, callback=dummy)
        ob = ReviewedObject()
        sm.execute(ob, 'publish')
        self.assertEqual(ob.state, 'published')
        sm.execute(ob, 'retract')
        self.assertEqual(ob.state, 'pending')
        sm.execute(ob, 'reject')
        self.assertEqual(ob.state, 'private')
        sm.execute(ob, 'submit')
        self.assertEqual(ob.state, 'pending')

        self.assertEqual(len(args), 4)
        self.assertEqual(args[0][0], ob)
        self.assertEqual(args[0][1], {'from_state': 'pending',
                                      'callback': dummy,
                                      'to_state': 'published',
                                      'id': 'publish'})
        self.assertEqual(args[1][0], ob)
        self.assertEqual(args[1][1], {'from_state': 'published',
                                      'callback': dummy,
                                      'to_state': 'pending',
                                      'id': 'retract'})
        self.assertEqual(args[2][0], ob)
        self.assertEqual(args[2][1], {'from_state': 'pending',
                                      'callback': dummy,
                                      'to_state': 'private',
                                      'id': 'reject'})
        self.assertEqual(args[3][0], ob)
        self.assertEqual(args[3][1], {'from_state': 'private',
                                      'callback': dummy,
                                      'to_state': 'pending',
                                      'id': 'submit'})

    def test_execute_error(self):
        sm = self._makeOne(initial_state='pending')
        ob = ReviewedObject()
        from repoze.bfg.workflow.statemachine import StateMachineError
        self.assertRaises(StateMachineError, sm.execute, ob, 'nosuch')

    def test_execute_guard(self):
        def guard(context, transition):
            raise ValueError
        sm = self._makeOne(initial_state='pending')
        self._add_transitions(sm)
        ob = ReviewedObject()
        self.assertRaises(ValueError, sm.execute, ob, 'publish', (guard,))

class ReviewedObject:
    pass
