from modules import faturamento, estoque, pedidos, financeiro

def load_dashboard_data():
    return {
        "faturamento": faturamento.get_data(),
        "estoque": estoque.get_data(),
        "pedidos": pedidos.get_data(),
        "financeiro": financeiro.get_data(),
    }