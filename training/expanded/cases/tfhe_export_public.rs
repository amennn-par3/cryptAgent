use tfhe::{ClientKey, ServerKey};

pub struct EvaluatorBundle {
    pub evaluation_key: ServerKey,
    pub decryption_key: Option<ClientKey>,
}

pub fn export_to_untrusted_evaluator(_client: ClientKey, server: ServerKey) -> EvaluatorBundle {
    EvaluatorBundle { evaluation_key: server, decryption_key: None }
}
