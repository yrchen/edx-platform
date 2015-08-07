define(['support/js/views/certificates'], function (CertificatesView) {
    'use strict';
    describe('CertificatesView', function () {

        beforeEach(function () {
            setFixtures('<div class="certificates-content"></div>');
            new CertificatesView({}).render();
        });

        it('can render itself', function () {
            expect(1).toBe(2);
        });
    });
});
